#!/usr/bin/env python3
"""The work-item hub: the only write path for every skill in evidence.

Design, in one paragraph. Many writers touch this hub -- parallel agents, sessions hours apart,
different machines reconciled by git -- so there is no shared mutable file and no lock. Each
actor appends to its own log, `hub/events/<role>/<actor>.jsonl`, and state is a deterministic
fold over every event. Appending never rewrites a line, so a git merge of two actors' work is a
trivial concatenation rather than a conflict. `qa-state.json` and friends become generated views
carrying a `generated_from` header: a view whose header does not match the hub is not truth, it
is the import branch, and `validate` says so. That is Phase 0 applied to artifacts.

Ordering and skew. `ts` is advisory, because clocks on two machines disagree and a QA session can
legitimately record an event with an earlier wall-clock time than the DEV event it answers.
Causality comes from `seq`, a per-actor monotonic counter, and from explicit `after` links. The
fold orders by (ts, actor, seq) but applies a transition only once its `after` events have been
applied, so the result is identical regardless of file read order. A `ts` that contradicts
causality is reported as skew, never silently reordered.

Duplicates. Every event carries `event_id` = "<actor>#<seq>". A repeated `event_id` is ignored by
the fold and reported by `validate`, so replaying an import twice is a no-op.

Authority. `shared/hub/model.json` holds the item types, their states, who may create them and
who may move them. The general invariant across every type is the one product-qa already uses:
the producer claims, a different role accepts. hub.py enforces it from that file -- adding a role
is rows in JSON, never a new code path here.

Usage:
    hub.py init [--engagement NAME]
    hub.py profile [--set k=v ...]
    hub.py add <type> <id> [--state S] [--owner ROLE] [--provenance P] [-f k=v ...]
    hub.py move <id> <state> [-f k=v ...]
    hub.py link <id> <rel> <target>
    hub.py note <id> <text>
    hub.py show <id>
    hub.py list [--mine] [--waiting-on ROLE] [--type T] [--state S] [--json]
    hub.py status
    hub.py validate [--json]
    hub.py import <report-dir>
    hub.py views
    hub.py dashboard [-o OUTDIR]
    hub.py iteration <n> [--note TEXT]

Every command takes --hub DIR (default: ./qa-reports/hub, or $PRODUCT_HUB).
Writes identify themselves with --actor NAME --role ROLE (or $PRODUCT_ACTOR/$PRODUCT_ROLE).

Standard library only. Windows and Linux.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

# The read commands print JSON and tables containing whatever a user typed. On Windows a piped
# stdout defaults to cp1252, so one arrow or check-mark in a title turned every `list`, `show`
# and `validate` into a UnicodeEncodeError traceback -- and `python -I`, which every skill
# prescribes, ignores PYTHONUTF8 and PYTHONIOENCODING. Reconfigure explicitly instead.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

SCHEMA_VERSION = 1
# shared/vocabulary.md. Kept here so a write can be refused rather than silently ignored
# by the verdict later.
SEVERITIES = ("critical", "blocker", "major", "minor", "polish")
DEFAULT_HUB = os.path.join("qa-reports", "hub")

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(os.path.dirname(HERE), "hub", "model.json")

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# No ':' -- on Windows `item-A:B.html` silently becomes a 0-byte file plus an NTFS alternate
# data stream, and the dashboard index then links to a page that does not exist.
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class HubError(Exception):
    """A rejected operation. The message names the rule that refused it."""


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------

def load_model(path=None):
    path = path or MODEL_PATH
    try:
        with io.open(path, "r", encoding="utf-8") as fh:
            model = json.load(fh)
    except OSError as exc:
        raise HubError("cannot read the item model at %s: %s" % (path, exc))
    except ValueError as exc:
        raise HubError("item model at %s is not valid JSON: %s" % (path, exc))
    if model.get("schema_version") != SCHEMA_VERSION:
        raise HubError("item model schema_version %r, this hub.py speaks %d"
                       % (model.get("schema_version"), SCHEMA_VERSION))
    return model


def type_def(model, item_type):
    types = model.get("types", {})
    if item_type not in types:
        raise HubError("unknown item type %r. Known types: %s"
                       % (item_type, ", ".join(sorted(types))))
    return types[item_type]


def states_of(tdef):
    states = {tdef["initial"]}
    for tr in tdef.get("transitions", []):
        states.add(tr["to"])
        states.update(tr.get("from", []))
    return states


# ---------------------------------------------------------------------------
# event log
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_ts(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def actor_log_path(hub, role, actor):
    if not SAFE_NAME.match(role or ""):
        raise HubError("role %r is not a safe directory name" % role)
    if not SAFE_NAME.match(actor or ""):
        raise HubError("actor %r is not a safe file name" % actor)
    return os.path.join(hub, "events", role, actor + ".jsonl")


def read_all_events(hub):
    """Read every actor log. Returns (events, notes).

    A line the fold cannot read is prefixed UNREADABLE and a line whose payload disagrees with
    the file holding it is prefixed MISATTRIBUTED; `validate` promotes both to problems. They
    were plain notes before, so `validate` exited 0 and the verdict went GREEN over a log the
    hub had failed to read.
    """
    events, notes = [], []
    root = os.path.join(hub, "events")
    if not os.path.isdir(root):
        # UNREADABLE, not a note: `validate` promotes these to problems, and "this hub is not
        # there" must never read as "this hub is clean". Pointed at a mistyped path, the old
        # note exited 0 and congratulated the operator.
        return events, ["UNREADABLE no events directory at %s -- there is no hub here" % root]
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace("\\", "/")
            # Read bytes and decode per line. Opening the file as text meant a single stray
            # byte anywhere in any log raised UnicodeDecodeError out of the fold -- a traceback
            # instead of a finding, which is the strongest possible violation of this hub's own
            # rule that one bad line must not make the whole hub unreadable.
            with io.open(path, "rb") as fh:
                raw_lines = fh.read().split(b"\n")
            decoded = []
            for lineno, raw in enumerate(raw_lines, 1):
                try:
                    decoded.append((lineno, raw.decode("utf-8")))
                except UnicodeDecodeError as exc:
                    notes.append("UNREADABLE %s line %d is not valid UTF-8: %s"
                                 % (rel, lineno, exc))
            if decoded:
                for lineno, line in decoded:
                    line = line.strip()
                    if not line or line.startswith("//"):
                        continue
                    try:
                        ev = json.loads(line)
                    except ValueError as exc:
                        notes.append("UNREADABLE %s line %d is not JSON: %s"
                                     % (rel, lineno, exc))
                        continue
                    if not isinstance(ev, dict):
                        notes.append("UNREADABLE %s line %d is not a JSON object"
                                     % (rel, lineno))
                        continue
                    ev["_src"] = rel
                    ev["_line"] = lineno
                    parts = rel.split("/")
                    if len(parts) != 2:
                        # A log must live under events/<ROLE>/<actor>.jsonl. One sitting directly
                        # under events/ has no attribution to check, so it is not folded at all.
                        notes.append(
                            "UNREADABLE %s line %d is not at events/<ROLE>/<actor>.jsonl -- it is "
                            "%d level(s) deep. Attribution comes from that exact shape, so this "
                            "line carries none and is not applied."
                            % (rel, lineno, len(parts)))
                        continue
                    path_role, path_actor = parts[-2], name[:-len(".jsonl")]
                    if ev.get("role") != path_role or ev.get("actor") != path_actor:
                        notes.append(
                            "MISATTRIBUTED %s line %d claims %s/%s but sits in %s/%s. The path "
                            "is the attribution, so the event is applied as %s/%s -- the payload "
                            "is only a claim about who wrote it."
                            % (rel, lineno, ev.get("role"), ev.get("actor"),
                               path_role, path_actor, path_role, path_actor))
                    # The path wins. Otherwise a line could claim any role simply by saying so.
                    ev["role"], ev["actor"] = path_role, path_actor
                    events.append(ev)
    return events, notes


def next_seq(hub, role, actor):
    path = actor_log_path(hub, role, actor)
    if not os.path.isfile(path):
        return 1
    last = 0
    with io.open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if isinstance(ev, dict) and isinstance(ev.get("seq"), int):
                last = max(last, ev["seq"])
    return last + 1


def append_event(hub, role, actor, event):
    """Append one event to this actor's own log. No other writer touches this file."""
    path = actor_log_path(hub, role, actor)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    seq = next_seq(hub, role, actor)
    event = dict(event)
    event.update({
        "v": SCHEMA_VERSION,
        "seq": seq,
        # Namespaced by role: `seq` counts within one (role, actor) FILE, so one person wearing
        # two hats produced two `actor#1` events and the fold silently dropped the second.
        "event_id": "%s/%s#%d" % (role, actor, seq),
        "actor": actor,
        "role": role,
        "ts": event.get("ts") or now_iso(),
    })
    ordered = {k: event[k] for k in
               ("v", "event_id", "seq", "ts", "actor", "role", "op") if k in event}
    for k in sorted(event):
        if k not in ordered and not k.startswith("_"):
            ordered[k] = event[k]
    with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(ordered, ensure_ascii=False) + "\n")
    return ordered


# ---------------------------------------------------------------------------
# the fold
# ---------------------------------------------------------------------------

class Hub:
    def __init__(self, hub_dir, model=None):
        self.dir = hub_dir
        self.model = model or load_model()
        self.items = {}
        self.meta = {"engagement": None, "iteration": None, "profile": {}}
        self.problems = []
        self.notes = []
        self.skew = []
        self.applied = []
        self._fold()

    # -- ordering ---------------------------------------------------------

    @staticmethod
    def _sort_key(ev):
        ts = parse_ts(ev.get("ts"))
        return (ts is None, ts or datetime.max.replace(tzinfo=timezone.utc),
                str(ev.get("actor") or ""), int(ev.get("seq") or 0))

    def _fold(self):
        events, notes = read_all_events(self.dir)
        self.notes += notes

        seen = set()
        deduped = []
        for ev in sorted(events, key=self._sort_key):
            eid = ev.get("event_id")
            if eid is None:
                self.problems.append("%s line %d has no event_id; it cannot be de-duplicated"
                                     % (ev.get("_src"), ev.get("_line")))
                continue
            if eid in seen:
                self.problems.append(
                    "duplicate event_id %s (%s line %d) -- ignored by the fold"
                    % (eid, ev.get("_src"), ev.get("_line")))
                continue
            if ev.get("v") != SCHEMA_VERSION:
                self.problems.append("%s line %d has schema v=%r, this hub.py speaks %d"
                                     % (ev.get("_src"), ev.get("_line"), ev.get("v"),
                                        SCHEMA_VERSION))
                continue
            seen.add(eid)
            deduped.append(ev)

        # Apply in causal order: an event waits for its `after` events.
        pending = list(deduped)
        done = set()
        progress = True
        while pending and progress:
            progress = False
            still = []
            for ev in pending:
                after = [a for a in (ev.get("after") or []) if a not in done]
                if after:
                    still.append(ev)
                    continue
                self._apply(ev)
                done.add(ev["event_id"])
                self.applied.append(ev)
                progress = True
            pending = still
        for ev in pending:
            self.problems.append(
                "%s line %d waits on events that never arrive: %s"
                % (ev.get("_src"), ev.get("_line"), ", ".join(ev.get("after") or [])))

        self._detect_skew()

    def _detect_skew(self):
        """An event applied after another but stamped earlier is clock skew.

        Causal order is what we applied; the timestamp merely disagrees. Report it, never
        reorder on it -- two machines' clocks differ and a QA session can legitimately stamp
        its answer before the DEV event it answers.
        """
        for item in self.items.values():
            prev_ts, prev_op = None, None
            for h in item["history"]:
                ts = parse_ts(h.get("ts"))
                if ts and prev_ts and ts < prev_ts:
                    self.skew.append(
                        "%s: %s is stamped %s but was applied after %s stamped %s "
                        "(clock skew across actors; causal order kept)"
                        % (item["id"], h.get("op"), h.get("ts"), prev_op,
                           prev_ts.isoformat()))
                if ts:
                    prev_ts, prev_op = ts, h.get("op")

    # -- application ------------------------------------------------------

    def _apply(self, ev):
        op = ev.get("op")
        handler = getattr(self, "_op_" + str(op).lower(), None)
        if handler is None:
            self.problems.append(
                "%s line %d has op %r, which this hub.py cannot apply -- the folded state is "
                "missing whatever that event did" % (ev.get("_src"), ev.get("_line"), op))
            return
        if not isinstance(ev.get("fields", {}), dict):
            self.problems.append("%s line %d has a non-object `fields`, so the folded state is "
                                 "missing it" % (ev.get("_src"), ev.get("_line")))
            ev = dict(ev, fields={})
        try:
            handler(ev)
        except HubError as exc:
            self.problems.append("%s line %d rejected on replay: %s"
                                 % (ev.get("_src"), ev.get("_line"), exc))
        except (AttributeError, TypeError, ValueError, KeyError) as exc:
            # A malformed payload is reported, never raised: one bad line must not make the
            # whole hub unreadable.
            self.problems.append("%s line %d could not be applied (%s: %s)"
                                 % (ev.get("_src"), ev.get("_line"),
                                    type(exc).__name__, exc))

    def _hist(self, item, ev, **extra):
        entry = {"ts": ev.get("ts"), "actor": ev.get("actor"), "role": ev.get("role"),
                 "op": ev.get("op"), "event_id": ev.get("event_id")}
        entry.update({k: v for k, v in extra.items() if v is not None})
        item["history"].append(entry)

    def _op_init(self, ev):
        self.meta["engagement"] = ev.get("engagement") or self.meta["engagement"]

    def _op_profile(self, ev):
        self.meta["profile"].update(ev.get("fields") or {})

    def _op_iteration(self, ev):
        self.meta["iteration"] = ev.get("iteration")
        self.meta.setdefault("iteration_history", []).append(
            {"iteration": ev.get("iteration"), "ts": ev.get("ts"), "actor": ev.get("actor"),
             "note": ev.get("note")})

    def _op_add(self, ev):
        iid = ev.get("item")
        if iid in self.items:
            self.problems.append("%s line %d re-creates item %s, which already exists; ids are "
                                 "names and are never reused"
                                 % (ev.get("_src"), ev.get("_line"), iid))
            return
        # Same check the CLI makes, here because the fold is what every write path reaches.
        # Adding it only to cmd_add left a hand-written log free to create F-9 beside f-9,
        # validate reporting zero problems, and the dashboard writing one page for both --
        # which is precisely the shape of the duplicate-hiding critical found in review:
        # a guard at a call site instead of in the function every path calls.
        clash = next((i for i in self.items if i.lower() == str(iid or "").lower()), None)
        if clash:
            self.problems.append(
                "%s line %d creates %s, which differs from the existing %s only in case. They "
                "collide as filenames on Windows and macOS, so the dashboard writes one page "
                "for both and one item's page is lost"
                % (ev.get("_src"), ev.get("_line"), iid, clash))
            return
        tdef = type_def(self.model, ev.get("type"))
        state = ev.get("state") or tdef["initial"]
        # A hand-written or forged line must not reach what the CLI refuses.
        creators = tdef.get("create") or []
        if creators and ev.get("role") not in creators:
            self.problems.append("%s line %d: role %s may not create a %s"
                                 % (ev.get("_src"), ev.get("_line"), ev.get("role"),
                                    ev.get("type")))
            return
        if not SAFE_ID.match(str(iid or "")):
            self.problems.append(
                "%s line %d creates an id %r the CLI would refuse. A path separator or colon in "
                "an id escapes or mangles the dashboard's output filenames."
                % (ev.get("_src"), ev.get("_line"), iid))
            return
        problem = create_problem(self.model, ev.get("type"), None, ev.get("fields"))
        if problem:
            self.problems.append("%s line %d: %s"
                                 % (ev.get("_src"), ev.get("_line"), problem))
            return
        if state != tdef["initial"]:
            self.problems.append(
                "%s line %d creates %s directly in %s, bypassing every transition rule. A %s is "
                "created in %s." % (ev.get("_src"), ev.get("_line"), iid, state,
                                    ev.get("type"), tdef["initial"]))
            return
        for problem in (field_authority_problem(self.model, ev.get("type"), ev.get("role"),
                                                ev.get("fields")),
                        severity_problem(self.model, ev.get("type"), ev.get("fields")),
                        guards_problem(ev.get("fields"))):
            if problem:
                self.problems.append("%s line %d: %s"
                                     % (ev.get("_src"), ev.get("_line"), problem))
                return
        self.items[iid] = {
            "id": iid, "type": ev.get("type"), "state": state,
            "owner_role": ev.get("owner") or ev.get("role"),
            "provenance": ev.get("provenance") or "authored",
            "fields": dict(ev.get("fields") or {}),
            "links": [], "notes": [], "history": [],
            "created_ts": ev.get("ts"), "created_by": ev.get("actor"),
            "iteration": self.meta.get("iteration"),
        }
        self._hist(self.items[iid], ev, to=state)

    def _op_move(self, ev):
        iid = ev.get("item")
        item = self.items.get(iid)
        if item is None:
            self.problems.append("%s line %d moves unknown item %s"
                                 % (ev.get("_src"), ev.get("_line"), iid))
            return
        to = ev.get("to")
        self.check_transition(item, to, ev.get("role"), ev.get("actor"),
                              dict(ev.get("fields") or {}), replaying=True)
        item["fields"].update(ev.get("fields") or {})
        frm, item["state"] = item["state"], to
        self._hist(item, ev, **{"from": frm, "to": to})

    def _op_set(self, ev):
        iid = ev.get("item")
        item = self.items.get(iid)
        if item is None:
            self.problems.append("%s line %d sets fields on unknown item %s"
                                 % (ev.get("_src"), ev.get("_line"), iid))
            return
        for problem in (severity_problem(self.model, item["type"], ev.get("fields")),
                        guards_problem(ev.get("fields")),
                        link_field_problem(self.items, item["id"], item["type"],
                                           ev.get("fields"))):
            if problem:
                self.problems.append("%s line %d: %s"
                                     % (ev.get("_src"), ev.get("_line"), problem))
                return
        tdef = type_def(self.model, item["type"])
        owned = tdef.get("fields_owned_by") or {}
        for key in (ev.get("fields") or {}):
            allowed = owned.get(key)
            if allowed and ev.get("role") not in allowed:
                self.problems.append(
                    "%s line %d: role %s may not set %r on a %s -- that field belongs to %s"
                    % (ev.get("_src"), ev.get("_line"), ev.get("role"), key,
                       item["type"], " or ".join(allowed)))
                continue
            item["fields"][key] = ev["fields"][key]
        self._hist(item, ev, fields=sorted(ev.get("fields") or {}))

    def _op_link(self, ev):
        iid, target, rel = ev.get("item"), ev.get("target"), ev.get("rel")
        item = self.items.get(iid)
        if item is None:
            self.problems.append("%s line %d links from unknown item %s"
                                 % (ev.get("_src"), ev.get("_line"), iid))
            return
        if rel not in self.model.get("link_types", []):
            self.notes.append("%s line %d uses unknown link type %r"
                              % (ev.get("_src"), ev.get("_line"), rel))
        if target not in self.items:
            self.problems.append(
                "%s line %d links %s --%s--> %s, but %s does not exist in the hub"
                % (ev.get("_src"), ev.get("_line"), iid, rel, target, target))
        item["links"].append({"rel": rel, "target": target})
        self._hist(item, ev, rel=rel, target=target)

    def _op_unlink(self, ev):
        iid, target, rel = ev.get("item"), ev.get("target"), ev.get("rel")
        item = self.items.get(iid)
        if item is None:
            self.problems.append("%s line %d unlinks from unknown item %s"
                                 % (ev.get("_src"), ev.get("_line"), iid))
            return
        before = len(item["links"])
        item["links"] = [l for l in item["links"]
                         if not (l["target"] == target and l["rel"] == rel)]
        if len(item["links"]) == before:
            self.problems.append("%s line %d retracts a link %s --%s--> %s that does not exist"
                                 % (ev.get("_src"), ev.get("_line"), iid, rel, target))
        self._hist(item, ev, rel=rel, target=target)

    def _op_note(self, ev):
        item = self.items.get(ev.get("item"))
        if item is None:
            self.problems.append("%s line %d notes unknown item %s"
                                 % (ev.get("_src"), ev.get("_line"), ev.get("item")))
            return
        item["notes"].append({"ts": ev.get("ts"), "actor": ev.get("actor"),
                              "text": ev.get("text")})
        self._hist(item, ev)

    # -- the rules --------------------------------------------------------

    def check_transition(self, item, to, role, actor, fields, replaying=False):
        """Raise HubError naming the rule that refuses this move.

        `replaying` distinguishes an invariant from a precondition. Role, required fields and
        different-actor are invariants: they were true when written and must still be true, so
        they are re-checked on every fold. "The computed verdict agreed" is a PRECONDITION --
        true at write time and not re-evaluable later, because by then the hub has moved on. The
        first version re-checked it during replay, which made a recorded GREEN permanently
        unreplayable the moment a generated view existed: the mid-fold hub looked stale to its
        own view, so the verdict came out NO VERDICT and refused an event that was already a
        fact.
        """
        tdef = type_def(self.model, item["type"])
        known = states_of(tdef)
        if to not in known:
            raise HubError("%s is not a state a %s can be in. States: %s"
                           % (to, item["type"], ", ".join(sorted(known))))

        candidates = [tr for tr in tdef.get("transitions", [])
                      if item["state"] in tr.get("from", []) and tr["to"] == to]
        self._replaying = replaying
        if not candidates:
            legal = sorted({tr["to"] for tr in tdef.get("transitions", [])
                            if item["state"] in tr.get("from", [])})
            raise HubError(
                "a %s in %s cannot move to %s. Legal moves from %s: %s"
                % (item["type"], item["state"], to, item["state"],
                   ", ".join(legal) or "(none -- terminal state)"))

        errors = []
        for tr in candidates:
            problem = self._transition_problem(item, tr, role, actor, fields, replaying)
            if problem is None:
                return tr
            errors.append(problem)
        raise HubError(errors[0])

    def _transition_problem(self, item, tr, role, actor, fields, replaying=False):
        roles = tr.get("roles") or []
        if roles and role not in roles:
            return ("role %s may not move a %s from %s to %s -- that transition belongs to %s. "
                    "The producer claims; a different role accepts."
                    % (role, item["type"], item["state"], tr["to"], " or ".join(roles)))

        # Required fields are checked against the fields supplied ON THIS EVENT, not against
        # whatever is already on the item. The earlier version OR-ed with item["fields"], which
        # made the guard dead on every path that mattered: a release reaching SHIPPED already
        # carried QA's `reason` from NO_VERDICT, so the operator's reason -- the one the method
        # insists on -- was never demanded, and the audit trail showed a reason-less ship that
        # read as reasoned. Presence, not truthiness: a metric reading of 0 is a reading.
        missing = [f for f in tr.get("requires_fields", [])
               if f not in fields or is_blank(fields[f])]
        if missing:
            return ("moving a %s to %s requires %s -- supplied on this move, not inherited from "
                    "an earlier one"
                    % (item["type"], tr["to"], ", ".join("-f %s=..." % m for m in missing)))

        owned = (type_def(self.model, item["type"]).get("fields_owned_by") or {})
        for key in fields:
            allowed = owned.get(key)
            if allowed and role not in allowed:
                return ("role %s may not set %r on a %s -- that field belongs to %s. "
                        "A move carries fields too; the owner rule applies to every write path."
                        % (role, key, item["type"], " or ".join(allowed)))

        for prior_state in tr.get("different_actor_from", []):
            for h in item["history"]:
                if h.get("to") == prior_state and h.get("actor") == actor:
                    return ("%s set %s to %s and may not also move it to %s. "
                            "The author does not grade their own work."
                            % (actor, item["id"], prior_state, tr["to"]))

        # HA-3: a `duplicate_of` that names nothing, or names the item itself, let a DEV take a
        # critical out of the verdict with one legal command. The transition is DEV's by design;
        # the target was simply never checked.
        problem = link_field_problem(self.items, item["id"], item["type"], fields)
        if problem:
            return problem

        # MG-2 / HA-14: §6 says a verdict is computed, never written -- and the dashboard said
        # NO VERDICT while this very transition wrote GREEN. The write path now asks the same
        # function the page does, so the two cannot disagree.
        if tr.get("requires_computed_verdict") and not replaying:
            try:
                sys.path.insert(0, HERE)
                import dashboard as _dash
                label, first_gap, _conditions = _dash.verdict(self)
            except Exception as exc:                       # noqa: BLE001
                return ("the verdict could not be computed, so it cannot be recorded (%s: %s)"
                        % (type(exc).__name__, exc))
            if label != tr["requires_computed_verdict"]:
                return ("the computed verdict is %r, not %r, so %s cannot be recorded as %s. "
                        "First condition without rows: %s. A verdict is computed, never written."
                        % (label, tr["requires_computed_verdict"], item["id"], tr["to"],
                           first_gap))

        if tr.get("requires_linked_cases_pass"):
            cases = [self.items.get(l["target"]) for l in item["links"]
                     if l["rel"] in ("verifies", "graded_by")]
            cases = [c for c in cases if c is not None and c["type"] == "case"]
            inbound = [c for c in self.items.values()
                       if c["type"] == "case" and any(
                           l["target"] == item["id"] and l["rel"] == "verifies"
                           for l in c["links"])]
            cases = {c["id"]: c for c in cases + inbound}.values()
            if not cases:
                return ("a %s cannot be accepted with no linked cases: its acceptance criteria "
                        "were never turned into anything that can fail" % item["type"])
            bad = sorted(c["id"] for c in cases if c["state"] not in ("PASS",))
            if bad:
                return ("%s cannot be accepted while its linked cases are not PASS: %s"
                        % (item["id"], ", ".join(bad)))
        return None

    # -- queries ----------------------------------------------------------

    def waiting_on(self, item):
        """Which role the item is currently waiting for, from the model alone.

        Escape hatches do not count. The earlier version unioned the roles on *every* outgoing
        transition, so a SHIPPED release was reported as awaiting the operator (because it can
        still be rolled back) and an AGREED requirement as awaiting the PO (because it can still
        be superseded). That made the delivery report's first and most-read section -- "blocked
        on a human" -- wrong by construction, in a tool whose own rule is to quote states rather
        than paraphrase them.
        """
        tdef = type_def(self.model, item["type"])
        roles = set()
        for tr in tdef.get("transitions", []):
            if tr.get("escape"):
                continue
            if item["state"] in tr.get("from", []):
                roles.update(tr.get("roles") or [])
        return sorted(roles)

    def validate(self):
        """Structural problems plus the invariants that are not single-transition rules."""
        out = list(self.problems)
        out += [n for n in self.notes
                if n.startswith("UNREADABLE") or n.startswith("MISATTRIBUTED")]

        for item in self.items.values():
            tdef = type_def(self.model, item["type"])
            if item["state"] not in states_of(tdef):
                out.append("%s is in %s, which is not a state a %s can be in"
                           % (item["id"], item["state"], item["type"]))

        # NEW is not a resting state: a finding handed over and left NEW is the failure
        # this rule exists to prevent.
        for item in self.items.values():
            if item["type"] != "finding" or item["state"] != "NEW":
                continue
            handed = any(h.get("op") == "move" for h in item["history"])
            if item["fields"].get("handed_over") or handed:
                out.append("finding %s is still NEW after being handed over. NEW is not a "
                           "resting state: it leaves with a decision and a reason." % item["id"])

        # A view without a matching hub is not truth.
        for name in ("qa-state.json", "fix-state.json"):
            path = os.path.join(os.path.dirname(self.dir), name)
            if not os.path.isfile(path):
                continue
            try:
                with io.open(path, "r", encoding="utf-8") as fh:
                    view = json.load(fh)
            except (OSError, ValueError) as exc:
                out.append("generated view %s cannot be read: %s" % (name, exc))
                continue
            header = view.get("generated_from") or {}
            stamp = header.get("event_count")
            digest = self._event_digest()
            body = {k: v for k, v in view.items() if k != "generated_from"}
            current = self.qa_state() if name == "qa-state.json" else self.fix_state()
            expected = {k: v for k, v in current.items() if k != "generated_from"}
            if body != expected:
                out.append("%s does not match what the hub would generate. A digest over event "
                           "ids could not see a hand-edited body; this compares the body itself. "
                           "Regenerate it with `hub.py views`." % name)
            if header.get("event_digest") not in (None, digest):
                out.append("%s carries a digest that does not match the hub's events. A row "
                           "count alone could not tell a hand-edited view from a current one; "
                           "regenerate it with `hub.py views`." % name)
            elif header.get("event_digest") is None and stamp is not None:
                out.append("%s predates digest stamping, so it cannot be told apart from a "
                           "hand-edited file. Regenerate it with `hub.py views`." % name)
            if stamp is None:
                out.append("%s has no generated_from header, so it cannot be told apart from a "
                           "hand-edited file. Regenerate it with `hub.py views`." % name)
            elif stamp != len(self.applied):
                out.append("%s was generated from %s events; the hub now has %d. The view is "
                           "stale -- regenerate it with `hub.py views`."
                           % (name, stamp, len(self.applied)))

        for item in self.items.values():
            for link in item["links"]:
                if link["target"] not in self.items:
                    out.append("%s links to %s, which does not exist"
                               % (item["id"], link["target"]))
        return out

    # -- generated views --------------------------------------------------

    def _event_digest(self):
        """A digest over the applied event ids.

        A row count alone could not tell a hand-edited view from a current one: editing the view
        while leaving its header intact passed `validate` clean, and so did fabricating a file
        with a forged `event_count`.
        """
        joined = "\n".join(e.get("event_id", "") for e in self.applied)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def _view_header(self):
        digest = self._event_digest()
        return {"generated_by": "hub.py", "generated_at": now_iso(),
                "event_count": len(self.applied), "event_digest": digest,
                "schema_version": SCHEMA_VERSION,
                "warning": "GENERATED FILE -- never hand-edit. The hub is the source of truth."}

    def qa_state(self):
        findings, cases = [], []
        for item in sorted(self.items.values(), key=lambda i: i["id"]):
            if item["type"] == "finding":
                findings.append({
                    "id": item["id"], "title": item["fields"].get("title"),
                    "severity": item["fields"].get("severity"),
                    "scope": item["fields"].get("scope"),
                    "status": item["state"],
                    "status_action": item["fields"].get("status_action"),
                    "closed_in": item["fields"].get("closed_in"),
                    "provenance": item["provenance"],
                })
            elif item["type"] == "case":
                cases.append({
                    "id": item["id"], "scope": item["fields"].get("scope"),
                    "action": item["fields"].get("action"),
                    "oracle": item["fields"].get("oracle"),
                    "guards": item["fields"].get("guards"),
                    "ran_under": item["fields"].get("ran_under"),
                    "touches": item["fields"].get("touches"),
                    "graded_by": item["fields"].get("graded_by"),
                    "result": item["state"],
                    "provenance": item["provenance"],
                    "finding": next((l["target"] for l in item["links"]
                                     if l["rel"] == "verifies"
                                     and self.items.get(l["target"], {}).get("type")
                                     == "finding"), None),
                })
        return {
            "generated_from": self._view_header(),
            "engagement": self.meta.get("engagement"),
            "iteration": self.meta.get("iteration"),
            "mandate": self.meta.get("profile", {}).get("mandate"),
            "findings": findings,
            "cases": cases,
            "not_verified": [
                {"what": i["fields"].get("action"), "why": i["fields"].get("reason"),
                 "cases": [i["id"]], "since_iteration": i.get("iteration")}
                for i in sorted(self.items.values(), key=lambda i: i["id"])
                if i["type"] == "case" and i["state"] in ("NOT_RUN", "BLOCKED")],
            "cleanup": [
                {"item": i["fields"].get("title") or i["id"],
                 "removable_by": i["fields"].get("removable_by"),
                 "cost": i["fields"].get("cost"), "status": i["state"],
                 "verified_by": i["fields"].get("verified_by")}
                for i in sorted(self.items.values(), key=lambda i: i["id"])
                if i["type"] == "cleanup"],
        }

    def fix_state(self):
        fixes = []
        for item in sorted(self.items.values(), key=lambda i: i["id"]):
            if item["type"] != "fix":
                continue
            fixes.append({
                "id": item["id"], "state": item["state"],
                "fixes": [l["target"] for l in item["links"] if l["rel"] == "fixes"],
                "commit": item["fields"].get("commit"),
                "build": item["fields"].get("build"),
                "test": item["fields"].get("test"),
                "root_cause": item["fields"].get("root_cause"),
            })
        return {"generated_from": self._view_header(),
                "engagement": self.meta.get("engagement"), "role": "DEV", "fixes": fixes}

    def write_views(self):
        out = os.path.dirname(self.dir)
        os.makedirs(out, exist_ok=True)
        written = []
        for name, payload in (("qa-state.json", self.qa_state()),
                              ("fix-state.json", self.fix_state())):
            path = os.path.join(out, name)
            with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(payload, fh, indent=1, ensure_ascii=False)
                fh.write("\n")
            written.append(path)
        return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def link_field_problem(items, item_id, item_type, fields):
    """`duplicate_of` must name a different, existing item of the same type.

    Checked on add, move AND set. It was a move-only check, so `set -f duplicate_of=<a PASS case>`
    made an open critical resolve to something the verdict counts as closed.
    """
    if "duplicate_of" not in (fields or {}):
        return None
    target = fields["duplicate_of"]
    if target == item_id:
        return "%s cannot be a duplicate of itself" % item_id
    other = (items or {}).get(target)
    if other is None:
        return ("%s names %s as duplicate_of, which does not exist in the hub. A duplicate must "
                "point at something someone can read." % (item_id, target))
    if other.get("type") != item_type:
        return ("%s is a %s; duplicate_of must name another %s"
                % (target, other.get("type"), item_type))
    return None


def field_authority_problem(model, item_type, role, fields):
    """Which supplied field this role may not set. Used by add, move and set alike.

    The earlier version applied `fields_owned_by` only in `set`, so `move -f severity=polish`
    and `add -f severity=polish` both walked past it -- which let a DEV un-block a release while
    the dashboard reported "no open critical" and the hub validated clean.
    """
    owned = (type_def(model, item_type).get("fields_owned_by") or {})
    for key in fields or {}:
        allowed = owned.get(key)
        if allowed and role not in allowed:
            return ("role %s may not set %r on a %s -- that field belongs to %s"
                    % (role, key, item_type, " or ".join(allowed)))
    return None


def create_problem(model, item_type, state, fields):
    """Create-time rules: the initial state only, and the fields a type cannot exist without."""
    tdef = type_def(model, item_type)
    if state is not None and state != tdef["initial"]:
        return ("a %s is created in %s and reaches %s only through a transition, which is where "
                "the role, required-field and different-actor rules live. Creating it directly "
                "in %s would bypass all of them."
                % (item_type, tdef["initial"], state, state))
    missing = [f for f in (tdef.get("requires_fields_on_create") or [])
               if f not in (fields or {}) or is_blank((fields or {})[f])]
    if missing:
        return ("a %s cannot be created without %s"
                % (item_type, ", ".join("-f %s=..." % m for m in missing)))
    return None


def severity_problem(model, item_type, fields):
    """A severity outside the vocabulary is worse than none: the verdict cannot see it."""
    if "severity" not in (fields or {}):
        return None
    value = fields["severity"]
    if not isinstance(value, str):
        return ("severity must be one of %s, not %r"
                % (", ".join(SEVERITIES), value))
    if value.strip().lower() not in SEVERITIES:
        return ("%r is not a severity. shared/vocabulary.md defines %s. An unrecognised value is "
                "invisible to the verdict, which is worse than no value at all."
                % (value, ", ".join(SEVERITIES)))
    return None


def guards_problem(fields):
    """`guards` must be an object with a known ceiling, or the verdict cannot read the stake."""
    if "guards" not in (fields or {}):
        return None
    g = fields["guards"]
    if not isinstance(g, dict):
        return ("guards must be an object, e.g. -f 'guards={\"class\":\"acked-write loss\","
                "\"ceiling\":\"critical\"}'. A prose guards value cannot be read by the "
                "verdict, and used to crash the dashboard outright. Got %r" % (g,))
    ceiling = (g.get("ceiling") or "")
    if not isinstance(ceiling, str) or ceiling.strip().lower() not in SEVERITIES:
        return ("guards.ceiling must be one of %s; got %r. The ceiling is the stake the row "
                "guards, and a row whose stake cannot be read is a row the verdict ignores."
                % (", ".join(SEVERITIES), g.get("ceiling")))
    return None


def is_blank(value):
    """Present-but-empty. `0` and `False`... are not the same thing here.

    `kv()` JSON-parses values, so `-f reason=null` arrived as None and `str(None).strip()` is
    "None" -- which read as present. `0` must still count, because a metric reading of zero is a
    reading; that was its own finding.
    """
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple, set)):
        return len(value) == 0 or (isinstance(value, str) and not value.strip())
    return False


def kv(pairs):
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise HubError("expected key=value, got %r" % pair)
        k, v = pair.split("=", 1)
        try:
            out[k] = json.loads(v)
        except ValueError:
            out[k] = v
    return out


def depends_on(hub_state, item, to_state):
    """Event ids this transition's checks depend on, beyond the item's own history."""
    out = []
    try:
        tdef = type_def(hub_state.model, item["type"])
    except HubError:
        return out
    relevant = [tr for tr in tdef.get("transitions", [])
                if item["state"] in tr.get("from", []) and tr["to"] == to_state]
    for tr in relevant:
        if tr.get("requires_linked_cases_pass"):
            for other in hub_state.items.values():
                if other["type"] != "case":
                    continue
                if any(l["target"] == item["id"] for l in other["links"]):
                    out += last_event_for(hub_state, other["id"])
            for link in item["links"]:
                out += last_event_for(hub_state, link["target"])
        if tr.get("requires_computed_verdict"):
            # The verdict reads the whole hub, so it depends on every item's latest event.
            for other in hub_state.items.values():
                out += last_event_for(hub_state, other["id"])
    return out


def last_event_for(hub_state, item_id):
    """The event_id this item was last touched by -- the `after` link that keeps the fold causal."""
    item = hub_state.items.get(item_id)
    if not item or not item["history"]:
        return []
    last = item["history"][-1].get("event_id")
    return [last] if last else []


def identity(args):
    actor = getattr(args, "actor", None) or os.environ.get("PRODUCT_ACTOR")
    role = getattr(args, "role", None) or os.environ.get("PRODUCT_ROLE")
    if not actor or not role:
        raise HubError("a write needs --actor NAME --role ROLE (or $PRODUCT_ACTOR / "
                       "$PRODUCT_ROLE). Every PASS is attributable or it is anonymous.")
    return actor, role


def resolve_hub(args):
    return (getattr(args, "hub", None) or os.environ.get("PRODUCT_HUB") or DEFAULT_HUB)


def cmd_init(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    os.makedirs(os.path.join(hub, "events"), exist_ok=True)
    append_event(hub, role, actor, {"op": "init", "engagement": args.engagement})
    print("initialised hub at %s" % hub)
    return 0


DOMAINS_DIR = os.path.join(os.path.dirname(HERE), "domains")


def known_domains():
    """The product classes this copy of the suite actually has a file for.

    Returns None when the directory is unreachable, which means "cannot validate" rather than
    "nothing is valid" -- refusing every class because an install is odd would be worse than the
    defect this guards.
    """
    try:
        names = os.listdir(DOMAINS_DIR)
    except OSError:
        return None
    return {n[:-3] for n in names if n.endswith(".md") and n != "README.md"}


def check_domains(fields):
    """`domains` names product classes, and the vocabulary is closed.

    skills/orient Step 2 says to pick from shared/domains/; skills/architecture and skills/prd
    then say to READ the chosen file for the fault catalogue and the load-bearing contracts.
    Exercising those two against a real product, `domains=[..., "self-hosted-deployment"]` was
    stored without comment and there is no such file -- so the catalogue for a class the product
    really is would never have been read, and nothing would ever have said so. Since `status`
    began printing this field, an unrecognised name reaches eleven skills with the profile's
    authority behind it.

    A class the suite genuinely lacks is a real case: orient says to work from the scope families
    and write the file afterwards. That goes in `domains_other`, which is kept and surfaced. The
    point is only that a typo must not be indistinguishable from a deliberate choice.
    """
    if "domains" not in fields:
        return
    value = fields["domains"]
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise HubError("domains must be a class name or a list of them, got %r" % (value,))
    known = known_domains()
    if known is None:
        return
    unknown = [str(d) for d in value if str(d) not in known]
    if not unknown:
        return
    import difflib
    lines = []
    for name in unknown:
        # A wrong suggestion is worse than none: a reader who accepts it reads the fault
        # catalogue for the wrong class, and the tool sounded sure. The first version of this
        # message offered "self-hosted-deployment -- did you mean payments?" at difflib's 0.4
        # cutoff. So require either a shared hyphen-token or a very close string, never a loose
        # character-overlap score.
        tokens = {t for t in str(name).lower().split("-") if len(t) > 2}
        near = [k for k in sorted(known)
                if tokens & {t for t in k.split("-") if len(t) > 2}
                or difflib.SequenceMatcher(None, str(name).lower(), k).ratio() >= 0.8][:3]
        lines.append("  %s -- %s" % (name, ("did you mean %s?" % ", ".join(near)) if near
                                     else "nothing close"))
    raise HubError(
        "no product class file for %d of the domains given:\n%s\n"
        "Every skill that reads the class opens shared/domains/<name>.md for the fault "
        "catalogue; a name with no file means that catalogue is silently never read. Pick from "
        "the %d available, or -- if the suite genuinely has no class for this product -- record "
        "it in `domains_other` with the reason and work from the scope families, as "
        "skills/orient Step 2 says."
        % (len(unknown), "\n".join(lines), len(known)))


def cmd_profile(args):
    hub = resolve_hub(args)
    if not args.set:
        h = Hub(hub)
        print(json.dumps(h.meta.get("profile", {}), indent=1))
        return 0
    actor, role = identity(args)
    fields = kv(args.set)
    check_domains(fields)
    append_event(hub, role, actor, {"op": "profile", "fields": fields})
    print("profile updated")
    return 0


def cmd_iteration(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    append_event(hub, role, actor,
                 {"op": "iteration", "iteration": args.n, "note": args.note})
    print("iteration %s recorded" % args.n)
    return 0


def cmd_add(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    h = Hub(hub)
    if not SAFE_ID.match(args.id or ""):
        raise HubError("%r is not a usable id" % args.id)
    if args.id in h.items:
        raise HubError("item %s already exists. Ids are names, not positions: never reuse or "
                       "renumber them." % args.id)
    # Ids that differ only in case collide on any case-insensitive filesystem, which is every
    # default Windows and macOS install. The dashboard writes one page per item as
    # item-<id>.html, so F-1 and f-1 produced a single file and one finding's page silently
    # overwrote the other's. Recorded as cosmetic in review; it is page-level data loss.
    clash = next((i for i in h.items if i.lower() == args.id.lower()), None)
    if clash:
        raise HubError("item %s already exists and %s differs from it only in case. They would "
                       "collide as filenames on Windows and macOS, and the dashboard would write "
                       "one page for both. Pick a distinct id." % (clash, args.id))
    tdef = type_def(h.model, args.type)
    creators = tdef.get("create") or []
    if creators and role not in creators:
        raise HubError("role %s may not create a %s -- that belongs to %s"
                       % (role, args.type, " or ".join(creators)))
    fields = kv(args.field)
    for problem in (create_problem(h.model, args.type, args.state, fields),
                    field_authority_problem(h.model, args.type, role, fields),
                    severity_problem(h.model, args.type, fields),
                    guards_problem(fields)):
        if problem:
            raise HubError(problem)
    state = tdef["initial"]
    append_event(hub, role, actor, {
        "op": "add", "item": args.id, "type": args.type, "state": state,
        "owner": args.owner or role, "provenance": args.provenance,
        "fields": fields})
    print("added %s %s in %s" % (args.type, args.id, state))
    return 0


def cmd_move(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    h = Hub(hub)
    item = h.items.get(args.id)
    if item is None:
        raise HubError("no item %s in the hub" % args.id)
    fields = kv(args.field)
    for problem in (severity_problem(h.model, item["type"], fields),
                    guards_problem(fields)):
        if problem:
            raise HubError(problem)
    h.check_transition(item, args.state, role, actor, fields)
    # The CLI checked this against the live state. If the check read OTHER items -- linked cases,
    # a duplicate target, the computed verdict -- those items' last events go in `after` too, or
    # the fold re-checks it against a state they had not reached yet and blames the wrong party.
    # Two machines ten minutes apart is normal, and that is exactly when it happened.
    after = last_event_for(h, args.id) + depends_on(h, item, args.state)
    append_event(hub, role, actor, {"op": "move", "item": args.id, "to": args.state,
                                    "fields": fields, "after": sorted(set(after))})
    print("%s: %s -> %s" % (args.id, item["state"], args.state))
    return 0


def cmd_set(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    h = Hub(hub)
    if args.id not in h.items:
        raise HubError("no item %s in the hub" % args.id)
    item = h.items[args.id]
    fields = kv(args.field)
    for problem in (field_authority_problem(h.model, item["type"], role, fields),
                    severity_problem(h.model, item["type"], fields),
                    guards_problem(fields),
                    link_field_problem(h.items, args.id, item["type"], fields)):
        if problem:
            raise HubError(problem)
    append_event(hub, role, actor, {"op": "set", "item": args.id, "fields": fields,
                                    "after": last_event_for(h, args.id)})
    print("%s updated" % args.id)
    return 0


def cmd_link(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    h = Hub(hub)
    for side in (args.id, args.target):
        if side not in h.items:
            raise HubError("no item %s in the hub; a link must join two real items" % side)
    # `link_types` is declared in the model and was enforced nowhere on write. `link A
    # blocked_by B` printed `A --blocked_by--> B` and exited 0; `validate` then mentioned it as a
    # NOTE, which does not fail. Exercising `architecture` put exactly that into a skill as the
    # prescribed command, so a reader would have run something that succeeds and records what the
    # hub cannot read -- worse than a command that fails, because nothing says so.
    declared = h.model.get("link_types") or []
    if declared and args.rel not in declared:
        import difflib
        near = difflib.get_close_matches(args.rel, declared, n=3, cutoff=0.55)
        near += [d for d in declared
                 if d not in near and (d in args.rel or args.rel in d)]
        raise HubError(
            "%r is not a link type. The model declares %s.%s A link the hub cannot read is "
            "worse than one it refuses: the write succeeds and nothing downstream sees it."
            % (args.rel, ", ".join(sorted(declared)),
               (" Did you mean %s?" % ", ".join(near[:3])) if near else ""))
    append_event(hub, role, actor, {"op": "link", "item": args.id, "rel": args.rel,
                                    "target": args.target,
                                    "after": last_event_for(h, args.id)
                                             + last_event_for(h, args.target)})
    print("%s --%s--> %s" % (args.id, args.rel, args.target))
    return 0


def cmd_unlink(args):
    """Retract a link. An event, not an erasure: `show` still records that it was retracted."""
    hub = resolve_hub(args)
    actor, role = identity(args)
    h = Hub(hub)
    item = h.items.get(args.id)
    if item is None:
        raise HubError("no item %s in the hub" % args.id)
    if not any(l["target"] == args.target and l["rel"] == args.rel for l in item["links"]):
        raise HubError("%s has no %s link to %s to retract" % (args.id, args.rel, args.target))
    append_event(hub, role, actor, {"op": "unlink", "item": args.id, "rel": args.rel,
                                    "target": args.target, "reason": args.reason,
                                    "after": last_event_for(h, args.id)})
    print("%s --%s--> %s retracted" % (args.id, args.rel, args.target))
    return 0


def cmd_note(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    h = Hub(hub)
    if args.id not in h.items:
        raise HubError("no item %s in the hub" % args.id)
    append_event(hub, role, actor, {"op": "note", "item": args.id, "text": args.text,
                                    "after": last_event_for(h, args.id)})
    print("noted on %s" % args.id)
    return 0


def cmd_show(args):
    h = Hub(resolve_hub(args))
    item = h.items.get(args.id)
    if item is None:
        raise HubError("no item %s in the hub" % args.id)
    view = dict(item)
    view["waiting_on"] = h.waiting_on(item)
    print(json.dumps(view, indent=1, ensure_ascii=False))
    return 0


def cmd_list(args):
    h = Hub(resolve_hub(args))
    rows = []
    for item in sorted(h.items.values(), key=lambda i: (i["type"], i["id"])):
        if args.type and item["type"] != args.type:
            continue
        if args.state and item["state"] != args.state:
            continue
        waiting = h.waiting_on(item)
        if args.waiting_on and args.waiting_on not in waiting:
            continue
        if args.mine:
            me = getattr(args, "role", None) or os.environ.get("PRODUCT_ROLE")
            if me and me not in waiting and item["owner_role"] != me:
                continue
        rows.append({"id": item["id"], "type": item["type"], "state": item["state"],
                     "owner": item["owner_role"], "waiting_on": waiting,
                     "title": item["fields"].get("title")})
    if args.json:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return 0
    if not rows:
        print("(no matching items)")
        return 0
    width = max(len(r["id"]) for r in rows)
    for r in rows:
        print("%-*s  %-12s %-22s %-10s %s" % (
            width, r["id"], r["type"], r["state"], ",".join(r["waiting_on"]) or "-",
            r["title"] or ""))
    return 0


def cmd_status(args):
    """The first thing a skill reads. Answers 'which iteration is this'."""
    hub_dir = resolve_hub(args)
    exists = os.path.isdir(os.path.join(hub_dir, "events"))
    if not exists:
        # The hint must be a command that RUNS. The earlier wording ended "otherwise
        # `hub.py init`", and that is rejected for missing --actor/--role -- so the first
        # thing a new engagement saw was advice that failed. Found by exercising
        # skills/orient against a real product; a hint you cannot paste is worse than none,
        # because it reads as a tool that does not work.
        print(json.dumps({"hub": hub_dir, "found": False,
                          "next": "no hub. If a prior qa-state.json or report dir exists, run "
                                  "`hub.py --hub %s import <dir> --actor NAME --role ROLE`; "
                                  "otherwise `hub.py --hub %s init --actor NAME --role ROLE`. "
                                  "Every write is attributable, init included."
                                  % (hub_dir, hub_dir)}, indent=1))
        return 0
    h = Hub(hub_dir)
    by_state = {}
    for item in h.items.values():
        by_state.setdefault(item["type"], {}).setdefault(item["state"], 0)
        by_state[item["type"]][item["state"]] += 1
    # `not_established` is surfaced here because skills/orient Step 6 REQUIRES the orienting
    # role to state what they could not establish, and warns that "every downstream skill
    # reads the profile and will otherwise assume you looked". Exercising orient against a
    # real product showed the profile accepted the field and NOTHING read it -- so the one
    # safeguard against downstream silent assumption was prose with no consumer. `status` is
    # the first thing every skill reads, so it is where the warning has to appear.
    profile = h.meta.get("profile") or {}
    unestablished = profile.get("not_established") or []
    if isinstance(unestablished, str):
        unestablished = [unestablished]
    # `domains` is surfaced for the same reason, found the same way. Eleven skills open with
    # `hub.py status  # mode, the product class, and what orient could not establish`, and the
    # middle claim was false: the product class lived only in `hub.py profile`. A skill that
    # believed the comment either guessed the class -- the exact failure that block was added to
    # stop -- or made an undocumented second call. `status` advertises it, so `status` prints it.
    domains = profile.get("domains") or []
    if isinstance(domains, str):
        domains = [domains]
    other = profile.get("domains_other") or []
    if isinstance(other, str):
        other = [other]
    out = {
        "hub": hub_dir, "found": True,
        "engagement": h.meta.get("engagement"),
        "iteration": h.meta.get("iteration"),
        "items": len(h.items), "events": len(h.applied),
        "by_type_state": by_state,
        "problems": len(h.validate()),
        "skew": len(h.skew),
        "profile_mode": profile.get("mode"),
        "domains": list(domains),
        "not_established": list(unestablished),
    }
    if other:
        # A class the suite has no file for. Surfaced so a reader can tell it from a typo, and so
        # the skill that goes looking for a fault catalogue knows there is none to find.
        out["domains_other"] = list(other)
    if not profile:
        out["next"] = ("no profile. Run /evidence:orient first, or every skill after this "
                       "one guesses the product class, the deploy branch and their vocabulary.")
    elif not domains:
        out["domains_warning"] = (
            "the profile names no product class. orient Step 2 requires choosing one from "
            "shared/domains/ -- and every skill that reads this field treats silence as 'no "
            "class applies', which is how a distributed store gets tested as a web app.")
    if profile and not unestablished:
        out["not_established_warning"] = (
            "the profile claims nothing was left unestablished. orient Step 6 requires that "
            "paragraph; an empty list means either a complete orientation or one that did not "
            "record its gaps, and a reader cannot tell which.")
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


def cmd_validate(args):
    h = Hub(resolve_hub(args))
    problems = h.validate()
    if args.json:
        print(json.dumps({"problems": problems, "notes": h.notes, "skew": h.skew}, indent=1))
    else:
        for p in problems:
            print("problem: %s" % p)
        for s in h.skew:
            print("skew:    %s" % s)
        for n in h.notes:
            print("note:    %s" % n)
        print("%d problem(s), %d skew, %d note(s)" % (len(problems), len(h.skew), len(h.notes)))
    return 2 if problems else 0


def cmd_import(args):
    """Import an old report dir. Ids are preserved; everything is marked reconstructed."""
    hub = resolve_hub(args)
    actor, role = identity(args)
    src = args.report_dir
    qa_path = os.path.join(src, "qa-state.json")
    if not os.path.isfile(qa_path):
        raise HubError("no qa-state.json in %s -- nothing to import" % src)
    with io.open(qa_path, "r", encoding="utf-8") as fh:
        old = json.load(fh)

    os.makedirs(os.path.join(hub, "events"), exist_ok=True)
    append_event(hub, role, actor, {"op": "init", "engagement": old.get("engagement")})
    if old.get("mandate"):
        append_event(hub, role, actor, {"op": "profile",
                                        "fields": {"mandate": old["mandate"]}})
    it = old.get("iteration")
    if it is not None:
        append_event(hub, role, actor, {"op": "iteration", "iteration": it,
                                        "note": "reconstructed by import"})

    def last_status(value):
        if isinstance(value, dict) and value:
            def ikey(k):
                try:
                    return (0, int(k))
                except (TypeError, ValueError):
                    return (1, 0)
            return value[sorted(value, key=ikey)[-1]]
        return value

    count = 0
    for f in old.get("findings", []):
        if not f.get("id"):
            continue
        append_event(hub, role, actor, {
            "op": "add", "item": f["id"], "type": "finding", "state": "NEW",
            "provenance": "reconstructed",
            "fields": {k: v for k, v in f.items()
                       if k in ("title", "severity", "scope", "status_action", "closed_in")}})
        count += 1
        st = last_status(f.get("status"))
        if st in ("VERIFIED FIXED", "CLOSED") or f.get("closed_in"):
            append_event(hub, role, actor, {
                "op": "note", "item": f["id"],
                "text": "imported as NEW with original status %r; re-triage rather than "
                        "assuming the old verdict still holds" % st})
    for c in old.get("cases", []):
        if not c.get("id"):
            continue
        append_event(hub, role, actor, {
            "op": "add", "item": c["id"], "type": "case", "state": "DESIGNED",
            "provenance": "reconstructed",
            "fields": {k: v for k, v in c.items()
                       if k in ("scope", "action", "oracle", "guards", "ran_under",
                                "touches", "graded_by")}})
        count += 1
        if c.get("finding"):
            append_event(hub, role, actor, {"op": "link", "item": c["id"],
                                            "rel": "verifies", "target": c["finding"]})
    print("imported %d item(s) from %s, ids unchanged, all marked provenance=reconstructed"
          % (count, src))
    print("NOTE: states were NOT imported. The report must say the register was reconstructed.")
    return 0


def cmd_views(args):
    h = Hub(resolve_hub(args))
    for path in h.write_views():
        print("wrote %s" % path)
    return 0


def cmd_dashboard(args):
    sys.path.insert(0, HERE)
    try:
        import dashboard as dash
    except ImportError as exc:
        raise HubError("dashboard module not available: %s" % exc)
    h = Hub(resolve_hub(args))
    out = args.out or os.path.join(os.path.dirname(h.dir), "dashboard")
    pages = dash.render(h, out)
    # The go/no-go must be readable without a browser: the release skill says this prints the
    # verdict and the condition table, and it printed a file path.
    label, first_gap, conditions = dash.verdict(h)
    print("VERDICT: %s" % label)
    if first_gap:
        print("  first condition without rows: %s" % first_gap)
    width = max(len(n) for n, _ok, _ev in conditions)
    for name, holds, evidence in conditions:
        print("  [%s] %-*s  %s" % ("yes" if holds else " NO", width, name, evidence[:60]))
    problems = h.validate()
    for problem in problems:
        print("  integrity: %s" % problem)
    print("wrote %d page(s) to %s" % (pages, out))
    print("open: %s" % os.path.join(out, "index.html"))
    return 2 if problems else 0


def build_parser():
    # --hub/--actor/--role are accepted BEFORE or AFTER the subcommand. argparse puts global
    # options before it, which is not what anyone writes: every documented example in six skills
    # trailed them, so the first command each non-QA role ran failed with an "unrecognized
    # arguments" error that named no fix. Registering them on a parent parser as well means the
    # natural order simply works, which is a better fix than correcting nine example lines.
    # SUPPRESS matters: with parents=, the subparser carries the SAME options, and a plain
    # default of None would overwrite a value given before the subcommand with nothing. With
    # SUPPRESS an unsupplied option leaves no attribute at all, so whichever side supplied it
    # wins and both orders work.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--hub", default=argparse.SUPPRESS,
                        help="hub directory (default ./qa-reports/hub or $PRODUCT_HUB)")
    common.add_argument("--actor", default=argparse.SUPPRESS,
                        help="who is writing (or $PRODUCT_ACTOR)")
    common.add_argument("--role", default=argparse.SUPPRESS,
                        help="which role (or $PRODUCT_ROLE)")

    ap = argparse.ArgumentParser(prog="hub.py", parents=[common],
                                 description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")

    def add_parser(name):
        return sub.add_parser(name, parents=[common])

    p = add_parser("init"); p.add_argument("--engagement"); p.set_defaults(fn=cmd_init)
    p = add_parser("profile"); p.add_argument("--set", action="append")
    p.set_defaults(fn=cmd_profile)
    p = add_parser("iteration"); p.add_argument("n", type=int)
    p.add_argument("--note"); p.set_defaults(fn=cmd_iteration)

    p = add_parser("add")
    p.add_argument("type"); p.add_argument("id")
    p.add_argument("--state"); p.add_argument("--owner")
    p.add_argument("--provenance", choices=["authored", "derived", "reconstructed"])
    p.add_argument("-f", "--field", action="append"); p.set_defaults(fn=cmd_add)

    p = add_parser("move"); p.add_argument("id"); p.add_argument("state")
    p.add_argument("-f", "--field", action="append"); p.set_defaults(fn=cmd_move)

    p = add_parser("set"); p.add_argument("id")
    p.add_argument("-f", "--field", action="append", required=True); p.set_defaults(fn=cmd_set)

    p = add_parser("link"); p.add_argument("id"); p.add_argument("rel")
    p.add_argument("target"); p.set_defaults(fn=cmd_link)

    p = add_parser("unlink"); p.add_argument("id"); p.add_argument("rel")
    p.add_argument("target"); p.add_argument("--reason"); p.set_defaults(fn=cmd_unlink)

    p = add_parser("note"); p.add_argument("id"); p.add_argument("text")
    p.set_defaults(fn=cmd_note)

    p = add_parser("show"); p.add_argument("id"); p.set_defaults(fn=cmd_show)

    p = add_parser("list")
    p.add_argument("--mine", action="store_true"); p.add_argument("--waiting-on")
    p.add_argument("--type"); p.add_argument("--state")
    p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_list)

    p = add_parser("status"); p.set_defaults(fn=cmd_status)
    p = add_parser("validate"); p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_validate)
    p = add_parser("import"); p.add_argument("report_dir"); p.set_defaults(fn=cmd_import)
    p = add_parser("views"); p.set_defaults(fn=cmd_views)
    p = add_parser("dashboard"); p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_dashboard)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    try:
        return args.fn(args)
    except HubError as exc:
        print("REJECTED: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
