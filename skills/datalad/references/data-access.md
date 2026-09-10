# Finding, retrieving, and releasing dataset content

## Finding published datasets

| Source | What it holds | How to reach it |
|---|---|---|
| [registry.datalad.org](https://registry.datalad.org) | Search across roughly 16,000 unique DataLad and git-annex datasets, indexing URL, dataset ID, branches, tags, and metadata | Search box supports a bare word, a quoted phrase, `AND`/`OR`/`NOT`, and field-specific terms; results give clone URLs |
| [datasets.datalad.org](https://datasets.datalad.org) | The DataLad superdataset, a nested collection of curated public datasets | `datalad clone ///` for the superdataset, `datalad clone ///<name>` for one entry |
| [OpenNeuroDatasets](https://github.com/OpenNeuroDatasets) | Public BIDS neuroimaging datasets from OpenNeuro, one repository per accession | `datalad clone https://github.com/OpenNeuroDatasets/ds00XXXX.git` |
| [dandisets](https://github.com/dandisets) | DANDI archive dandisets, mostly neurophysiology in NWB | `datalad clone https://github.com/dandisets/000XXX.git` |

The `///` shortcut is a DataLad resource identifier that resolves to the superdataset on
`datasets.datalad.org`. Because that superdataset is itself made of subdatasets, cloning
it gives a browsable tree of dataset names with no data in it, which is the intended way
to explore before choosing.

## Cloning

```
datalad clone [-h] [-d DATASET] [-D DESCRIPTION] [--reckless
    [auto|ephemeral|shared-...]] [-m MESSAGE] [-c PROC] [--version]
    SOURCE [PATH] ...
```

`SOURCE` accepts a URL, a local path, the `///` shortcut, or a RIA store URL such as
`ria+http://store.datalad.org#~hcp-openaccess`.

- `-d/--dataset` registers the new clone as a subdataset of the given parent, which is the
  correct way to bring external data into a project rather than copying it in.
- `--reckless auto` hard-links content between clones on the same filesystem, and
  `--reckless ephemeral` symlinks the annex to the origin's annex. Both trade safety for
  speed and disk, and both are recorded in local config and inherited by subdatasets. Use
  them for throwaway clones on a cluster, not for anything you will edit and push. For
  maintaining multiple concurrent checkouts of the same dataset without re-cloning, see
  the [git worktree workflow with DataLad](https://blog.datalad.org/posts/git-worktree-workflow/)
  post.
- `-D/--description` labels this particular copy. git-annex reports that label in
  `whereis` output, so a meaningful description ("scratch on cluster node") is what makes
  copy tracking readable later.

## Retrieving content

```
datalad get [-h] [-s LABEL] [-d PATH] [-r] [-R LEVELS] [-n] [-c PROC] [-D
    DESCRIPTION] [--reckless [auto|ephemeral|shared-...]] [-J NJOBS]
    [--data {anything|nothing|auto|auto-if-wanted}] [--version]
    [PATH ...]
```

- `-r/--recursive` descends into subdatasets, and `-R/--recursion-limit` bounds the depth.
  `-R existing` limits recursion to subdatasets already installed.
- `-n/--no-data` installs subdatasets without fetching any file content. This is the usual
  first move on a nested dataset: get the structure, look at it, then fetch selectively.
- `-s/--source` names a specific sibling to fetch from when several could serve the file.
- `-J/--jobs` parallelises retrieval, and `-J auto` uses the configured maximum. On a
  dataset of many small files this is the difference between minutes and hours.

When resolving where a subdataset lives, DataLad ranks candidate locations by cost,
considering the recorded URL, the superdataset's remote URL, and configured URL templates.
A subdataset that fails to install from its recorded URL can often still be reached
through the superdataset's own hosting.

## Annex content states

Every annexed file has two things that can independently exist:

1. The **pointer**, tracked in Git. It is a symlink into `.git/annex/objects/`, or a small
   plain file containing an annex key on filesystems without symlinks. Deleting it removes
   the file from the dataset.
2. The **content**, the actual bytes. They live in the local annex, on a remote, or both.

| Pointer | Content local | What you see |
|---|---|---|
| present | present | Normal file, readable |
| present | absent | Listed by `ls`, unreadable, restorable with `datalad get` |
| absent | not applicable | Gone from the dataset's working tree |

Inspect the state rather than guessing:

```bash
datalad status --annex           # local content summary for the dataset
git annex whereis <path>         # which repositories hold this file, and how many copies
git annex whereis --json <path>  # same, machine-readable, one JSON object per line
git annex list <path>            # compact matrix of files against remotes
```

`git annex whereis` reports the last information received from remotes and does not
contact them, so a remote that has since lost the file will still be listed. Treat it as a
record of belief, not a live check.

## Editing annexed files

git-annex write-protects annexed content, so a direct write to an annexed file fails with
a permission error even as the owner. That is deliberate: the file's content is
content-addressed and shared by hard link with the annex object, so writing in place would
corrupt every other reference to it.

```bash
datalad unlock <path>            # make it writable
# edit
datalad save -m "revise <path>"  # re-annexes and re-locks
```

Inside `datalad run`, declaring the file with `--output` performs the unlock
automatically, which is why the flag matters beyond documentation.

## Releasing content

```
datalad drop [-h] [--what {filecontent|allkeys|datasets|all}] [--reckless
    {modification|availability|undead|kill}] [-d DATASET] [-r] [-R LEVELS] [-J NJOBS]
    [--nocheck] [--if-dirty IF_DIRTY] [--version] [PATH ...]
```

- `--what filecontent` is the default and drops only file content, leaving pointers and
  the dataset intact.
- `--what allkeys` drops all keys including those not currently in the working tree,
  `--what datasets` uninstalls subdatasets, and `--what all` does both.
- `--reckless availability` overrides the check that another copy exists. This is the
  option that loses data when the check was right.
- `--reckless modification` allows dropping despite unsaved modifications,
  `--reckless undead` proceeds when the annex believes a copy exists somewhere
  unreachable, and `--reckless kill` is a last-resort removal.
- `--nocheck` and `--if-dirty` are deprecated. `--nocheck` is replaced by
  `--reckless availability`; `--if-dirty` is ignored entirely.

The real check is `datalad drop`'s own refusal to remove content it cannot verify
elsewhere; the commands below are a pre-flight look at what `whereis` already believes:

```bash
git annex whereis <path>                                # read the copy list yourself
git annex whereis --json <path> | jq '.whereis | length'  # count known copies
datalad push --to store   # make a second copy where none was, then
datalad drop <path>
```

`whereis` prints one `N copies` line per file, so a pipe into `grep -c 'copies'` returns
the file count, not the copy count — for a single file it always prints `1`, whether the
content exists in five places or nowhere but the local annex. The JSON form is what you
want when a script has to decide.

Never use `rm` or `git rm` on an annexed file to free space. `rm` leaves the pointer
pointing at nothing while the annex object survives, and `git rm` removes the pointer
without dropping the object. Both leave the dataset in a state that has to be repaired
rather than simply reverted.

## Repair and verification

`fsck` belongs to git-annex, not to DataLad, so call it directly:

```bash
git annex fsck                       # verify local content against recorded checksums
git annex fsck --fast                # skip checksum verification, check presence only
git annex fsck --from <remote>       # verify what a remote claims to hold
git annex unused                     # find annex objects no longer referenced
git annex dropunused all             # remove them
```

Run `git annex fsck --from <remote>` after any suspicion that a remote lost data, since it
is the only thing that replaces recorded belief with a live check. Run
`datalad wtf --section dependencies` when behaviour is inconsistent with the documentation,
since an old git-annex is behind a large share of confusing errors; DataLad 1.6 was
released alongside git-annex 10.x and drift from that pairing is the first thing to check.
