#!/usr/bin/env python3
"""The work-item hub: the only write path for every skill in product-suite.

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
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

SCHEMA_VERSION = 1
DEFAULT_HUB = os.path.join("qa-reports", "hub")

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(os.path.dirname(HERE), "hub", "model.json")

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


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
    """Read every actor log. Returns (events, notes). A bad line is a note, never fatal."""
    events, notes = [], []
    root = os.path.join(hub, "events")
    if not os.path.isdir(root):
        return events, ["no events directory at %s" % root]
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace("\\", "/")
            with io.open(path, "r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line or line.startswith("//"):
                        continue
                    try:
                        ev = json.loads(line)
                    except ValueError as exc:
                        notes.append("%s line %d is not JSON: %s" % (rel, lineno, exc))
                        continue
                    if not isinstance(ev, dict):
                        notes.append("%s line %d is not an object" % (rel, lineno))
                        continue
                    ev["_src"] = rel
                    ev["_line"] = lineno
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
        "event_id": "%s#%d" % (actor, seq),
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
            self.notes.append("unknown op %r (%s line %d)"
                              % (op, ev.get("_src"), ev.get("_line")))
            return
        try:
            handler(ev)
        except HubError as exc:
            self.problems.append("%s line %d rejected on replay: %s"
                                 % (ev.get("_src"), ev.get("_line"), exc))

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
        tdef = type_def(self.model, ev.get("type"))
        state = ev.get("state") or tdef["initial"]
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
                              dict(ev.get("fields") or {}))
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

    def check_transition(self, item, to, role, actor, fields):
        """Raise HubError naming the rule that refuses this move."""
        tdef = type_def(self.model, item["type"])
        known = states_of(tdef)
        if to not in known:
            raise HubError("%s is not a state a %s can be in. States: %s"
                           % (to, item["type"], ", ".join(sorted(known))))

        candidates = [tr for tr in tdef.get("transitions", [])
                      if item["state"] in tr.get("from", []) and tr["to"] == to]
        if not candidates:
            legal = sorted({tr["to"] for tr in tdef.get("transitions", [])
                            if item["state"] in tr.get("from", [])})
            raise HubError(
                "a %s in %s cannot move to %s. Legal moves from %s: %s"
                % (item["type"], item["state"], to, item["state"],
                   ", ".join(legal) or "(none -- terminal state)"))

        errors = []
        for tr in candidates:
            problem = self._transition_problem(item, tr, role, actor, fields)
            if problem is None:
                return tr
            errors.append(problem)
        raise HubError(errors[0])

    def _transition_problem(self, item, tr, role, actor, fields):
        roles = tr.get("roles") or []
        if roles and role not in roles:
            return ("role %s may not move a %s from %s to %s -- that transition belongs to %s. "
                    "The producer claims; a different role accepts."
                    % (role, item["type"], item["state"], tr["to"], " or ".join(roles)))

        missing = [f for f in tr.get("requires_fields", [])
                   if not (fields.get(f) or item["fields"].get(f))]
        if missing:
            return ("moving a %s to %s requires %s"
                    % (item["type"], tr["to"], ", ".join("-f %s=..." % m for m in missing)))

        for prior_state in tr.get("different_actor_from", []):
            for h in item["history"]:
                if h.get("to") == prior_state and h.get("actor") == actor:
                    return ("%s set %s to %s and may not also move it to %s. "
                            "The author does not grade their own work."
                            % (actor, item["id"], prior_state, tr["to"]))

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
        """Which role the item is currently waiting for, from the model alone."""
        tdef = type_def(self.model, item["type"])
        roles = set()
        for tr in tdef.get("transitions", []):
            if item["state"] in tr.get("from", []):
                roles.update(tr.get("roles") or [])
        return sorted(roles)

    def validate(self):
        """Structural problems plus the invariants that are not single-transition rules."""
        out = list(self.problems)

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
            stamp = (view.get("generated_from") or {}).get("event_count")
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

    def _view_header(self):
        return {"generated_by": "hub.py", "generated_at": now_iso(),
                "event_count": len(self.applied), "schema_version": SCHEMA_VERSION,
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


def last_event_for(hub_state, item_id):
    """The event_id this item was last touched by -- the `after` link that keeps the fold causal."""
    item = hub_state.items.get(item_id)
    if not item or not item["history"]:
        return []
    last = item["history"][-1].get("event_id")
    return [last] if last else []


def identity(args):
    actor = args.actor or os.environ.get("PRODUCT_ACTOR")
    role = args.role or os.environ.get("PRODUCT_ROLE")
    if not actor or not role:
        raise HubError("a write needs --actor NAME --role ROLE (or $PRODUCT_ACTOR / "
                       "$PRODUCT_ROLE). Every PASS is attributable or it is anonymous.")
    return actor, role


def resolve_hub(args):
    return args.hub or os.environ.get("PRODUCT_HUB") or DEFAULT_HUB


def cmd_init(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    os.makedirs(os.path.join(hub, "events"), exist_ok=True)
    append_event(hub, role, actor, {"op": "init", "engagement": args.engagement})
    print("initialised hub at %s" % hub)
    return 0


def cmd_profile(args):
    hub = resolve_hub(args)
    if not args.set:
        h = Hub(hub)
        print(json.dumps(h.meta.get("profile", {}), indent=1))
        return 0
    actor, role = identity(args)
    append_event(hub, role, actor, {"op": "profile", "fields": kv(args.set)})
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
    tdef = type_def(h.model, args.type)
    creators = tdef.get("create") or []
    if creators and role not in creators:
        raise HubError("role %s may not create a %s -- that belongs to %s"
                       % (role, args.type, " or ".join(creators)))
    state = args.state or tdef["initial"]
    if state not in states_of(tdef):
        raise HubError("%s is not a state a %s can be in" % (state, args.type))
    append_event(hub, role, actor, {
        "op": "add", "item": args.id, "type": args.type, "state": state,
        "owner": args.owner or role, "provenance": args.provenance,
        "fields": kv(args.field)})
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
    h.check_transition(item, args.state, role, actor, fields)
    append_event(hub, role, actor, {"op": "move", "item": args.id, "to": args.state,
                                    "fields": fields, "after": last_event_for(h, args.id)})
    print("%s: %s -> %s" % (args.id, item["state"], args.state))
    return 0


def cmd_set(args):
    hub = resolve_hub(args)
    actor, role = identity(args)
    h = Hub(hub)
    if args.id not in h.items:
        raise HubError("no item %s in the hub" % args.id)
    item = h.items[args.id]
    tdef = type_def(h.model, item["type"])
    owned = tdef.get("fields_owned_by") or {}
    fields = kv(args.field)
    for key in fields:
        allowed = owned.get(key)
        if allowed and role not in allowed:
            raise HubError("role %s may not set %r on a %s -- that field belongs to %s"
                           % (role, key, item["type"], " or ".join(allowed)))
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
    append_event(hub, role, actor, {"op": "link", "item": args.id, "rel": args.rel,
                                    "target": args.target,
                                    "after": last_event_for(h, args.id)
                                             + last_event_for(h, args.target)})
    print("%s --%s--> %s" % (args.id, args.rel, args.target))
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
            me = args.role or os.environ.get("PRODUCT_ROLE")
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
        print(json.dumps({"hub": hub_dir, "found": False,
                          "next": "no hub. If a prior qa-state.json or report dir exists, run "
                                  "`hub.py import <dir>`; otherwise `hub.py init`."}, indent=1))
        return 0
    h = Hub(hub_dir)
    by_state = {}
    for item in h.items.values():
        by_state.setdefault(item["type"], {}).setdefault(item["state"], 0)
        by_state[item["type"]][item["state"]] += 1
    print(json.dumps({
        "hub": hub_dir, "found": True,
        "engagement": h.meta.get("engagement"),
        "iteration": h.meta.get("iteration"),
        "items": len(h.items), "events": len(h.applied),
        "by_type_state": by_state,
        "problems": len(h.validate()),
        "skew": len(h.skew),
    }, indent=1, ensure_ascii=False))
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
    print("wrote %d page(s) to %s" % (pages, out))
    print("open: %s" % os.path.join(out, "index.html"))
    return 2 if h.validate() else 0


def build_parser():
    ap = argparse.ArgumentParser(prog="hub.py", description=__doc__.strip().splitlines()[0])
    ap.add_argument("--hub", help="hub directory (default ./qa-reports/hub or $PRODUCT_HUB)")
    ap.add_argument("--actor", help="who is writing (or $PRODUCT_ACTOR)")
    ap.add_argument("--role", help="which role (or $PRODUCT_ROLE)")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("init"); p.add_argument("--engagement"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("profile"); p.add_argument("--set", action="append")
    p.set_defaults(fn=cmd_profile)
    p = sub.add_parser("iteration"); p.add_argument("n", type=int)
    p.add_argument("--note"); p.set_defaults(fn=cmd_iteration)

    p = sub.add_parser("add")
    p.add_argument("type"); p.add_argument("id")
    p.add_argument("--state"); p.add_argument("--owner")
    p.add_argument("--provenance", choices=["authored", "derived", "reconstructed"])
    p.add_argument("-f", "--field", action="append"); p.set_defaults(fn=cmd_add)

    p = sub.add_parser("move"); p.add_argument("id"); p.add_argument("state")
    p.add_argument("-f", "--field", action="append"); p.set_defaults(fn=cmd_move)

    p = sub.add_parser("set"); p.add_argument("id")
    p.add_argument("-f", "--field", action="append", required=True); p.set_defaults(fn=cmd_set)

    p = sub.add_parser("link"); p.add_argument("id"); p.add_argument("rel")
    p.add_argument("target"); p.set_defaults(fn=cmd_link)

    p = sub.add_parser("note"); p.add_argument("id"); p.add_argument("text")
    p.set_defaults(fn=cmd_note)

    p = sub.add_parser("show"); p.add_argument("id"); p.set_defaults(fn=cmd_show)

    p = sub.add_parser("list")
    p.add_argument("--mine", action="store_true"); p.add_argument("--waiting-on")
    p.add_argument("--type"); p.add_argument("--state")
    p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_list)

    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("validate"); p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("import"); p.add_argument("report_dir"); p.set_defaults(fn=cmd_import)
    p = sub.add_parser("views"); p.set_defaults(fn=cmd_views)
    p = sub.add_parser("dashboard"); p.add_argument("-o", "--out")
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
