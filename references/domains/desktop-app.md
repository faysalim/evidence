# Domain: desktop application

An installed application with an installer, an auto-updater, a code-signing chain, OS integration, local
data, and often a CLI beside the GUI that has a different user and a different bug population.

## Do the thing

> It runs from your build output, signed with your development certificate, on the machine that compiled
> it. Install the **signed public installer of the previous release** on a clean machine, as a
> **non-administrator**, create data, let it auto-update, and open your data. **"It launches" is this
> domain's HTTP 200.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | download page, checksums, signing and requirement claims | own | |
| 2 Primary product | the application | own ×2 | split: GUI vs CLI / headless — different users, different defects |
| 3 Control plane | account or licence portal | N/A or own | |
| 4 Deployment | installer, silent / MSI install, per-user vs per-machine, uninstall | own | |
| 5 Entitlement | activation, offline licence, seat transfer | own | |
| 6 Secondary | plugins, shell integration, file associations | →2 | |
| 7 Telemetry | crash reporting, opt-in state, what is sent | →8 | |
| 8 Security | signing chain, update-channel integrity, local data at rest, privilege use | own | |
| 9 Documentation | install guide, requirements, CLI reference | own | |
| 10 State under fault | crash with unsaved work, disk full, file locks, two instances | own | |
| 11 Upgrade | **auto-update from the shipped previous version**, N-2, downgrade | own | |
| 12 Experience | first launch, OS trust prompts, crash recovery | own | |

**Usual set: 1,2×2,4,5,8,9,10,11,12 own + 6→2, 7→8 = 10 agents.**

## Failure catalogue

Install as a non-administrator · install over an existing version · install on a clean VM with no runtime
or redistributable present · uninstall then reinstall · an install path containing spaces and non-ASCII
characters · a roaming or network user profile · offline install · a machine with SmartScreen, Gatekeeper
or an enterprise allow-list · auto-update interrupted mid-download · update while the application is
running · the oldest supported OS version · display scaling at 125% and 150%, and a multi-monitor setup
with mixed scaling · a locale that uses comma decimals · antivirus quarantine · disk full while saving ·
the process killed with unsaved work · two instances at once · a file opened from a network share.

## Defect classes to look for by name

**A binary the operating system does not trust** — an unsigned, wrongly signed or untimestamped artifact,
which means the product never starts for a real customer · an installer that needs administrator rights
where the documentation says it does not · an uninstaller leaving data, services, registry keys or secrets
behind · **an auto-update that fails from the one version it must update from**, the shipped previous
release · settings, licence or local data lost on update · a crash that discards unsaved work with no
recovery file · a missing-runtime failure presented as a generic error · path, locale or encoding
mishandling · two instances corrupting a shared local store · display scaling that makes the UI unusable ·
a CLI whose flags contradict the GUI's labels.

## Evidence and severity

**A clean VM snapshot per run is the harness.** An application tested on the development machine is tested
with your runtimes, your certificates and your administrator rights already in place, which disqualifies
most of this domain's evidence. Record per run: OS name and version, architecture, install mode
(per-user / per-machine), the signing chain as the OS reports it, display scaling, locale, and **the exact
previous version used as the upgrade source**.

`evidence-standard.md` → *Migrations, upgrades and restores* (the update is an upgrade with the user's data
in it), and the matrix method from *Mobile builds on a device matrix*, which generalises directly to
OS × scaling × locale.

| Observation | Severity |
|---|---|
| The OS refuses to run the signed artifact | **critical** — nobody can run the product |
| Data loss on update | **critical** |
| Update broken from the shipped previous version | **critical** |
| Uninstall leaving credentials or licence material behind | **blocker** |
| Administrator rights required where the docs say otherwise | **blocker** — it blocks enterprise deployment |
| Scaling or locale breakage | **major** |

## Experience

**Who the user is:** the person installing on a locked-down corporate machine without administrator
rights, and the daily user afterwards.

**Where it lives:** first launch to first useful action; what an OS trust prompt says and whether the
download page prepares the user for it; update interruption; crash recovery; and whether the CLI and the
GUI describe the same product.

**First success is:** installed on a clean machine by a non-administrator, the core task completed once,
and still working after a reboot.

**Do the thing, for experience:**

> On a clean VM with no administrator rights, install from the public download link and complete the core
> task using only what the download page tells you.

**Defect classes:** a trust warning with no guidance, which users abandon rather than click through · an
installer that silently chooses per-machine and then fails · an update prompt that interrupts work with no
option to defer · a crash with no recovery offer · flags and labels that disagree between CLI and GUI.

**Evidence note:** the OS's own trust UI is kind-4 evidence that carries a named cost, exactly as platform
policy does for mobile. A Gatekeeper or SmartScreen block is not a convention violation — it is an
enforced gate, and the cost is every install that does not happen.

## Domain gotchas

- Your development machine is not a clean machine, and this is the domain where that sentence costs the
  most. Budget for a VM with snapshots before anything else.
- **Never produce a signed or obfuscated distributable under a trial licence of your own build tooling.**
  A trial can bake an expiry into the artifact you ship. Test the pre-built release artifact instead.
- Code-signing certificates expire, and **timestamping** is what keeps already-shipped builds valid. Check
  both, and check what the OS says rather than what the build log says.
- Auto-update needs a real previous version and the real update channel. A local feed proves the
  mechanism, not the shipped path — say which one you proved.
- Antivirus false positives are a genuine finding with a real support cost, not an environment problem.
- Uninstall tests leave residue that changes the next run. Snapshot, test, roll back.
