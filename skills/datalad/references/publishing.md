# Siblings, publishing, and credentials

## The two-target model

A DataLad dataset almost never publishes to one place. The Git history and the annexed
content usually go to different targets, because Git hosting services will not store the
data. The normal shape is a Git sibling plus a storage sibling, with a declared dependency
between them.

Getting this wrong produces the most common broken publication: collaborators clone
successfully, see every file listed, and then find every `datalad get` failing because the
content was never uploaded anywhere reachable.

## Managing siblings

```
datalad siblings [-h] [-d DATASET] [-s NAME] [--url [URL]] [--pushurl PUSHURL]
    [-D DESCRIPTION] [--fetch] [--as-common-datasrc NAME] [--publish-depends SIBLINGNAME]
    [--publish-by-default REFSPEC] [--annex-wanted EXPR] [--annex-required EXPR]
    [--annex-group EXPR] [--annex-groupwanted EXPR] [--inherit] [--no-annex-info]
    [-r] [-R LEVELS] [--version] [{query|add|remove|configure|enable}]
```

Five actions. `query` is the default and reports known siblings. `add` and `configure` are
the same operation except that adding a sibling whose name already exists fails while
reconfiguring does not. `enable` completes access for a git-annex special remote in a
fresh clone. `remove` de-configures a sibling.

Options that carry real consequences:

- `--publish-depends SIBLINGNAME` adds "a dependency such that the given existing sibling
  is always published prior to the new sibling". Set this on the Git sibling, naming the
  storage sibling, and the ordering problem stops being something anyone has to remember.
- `--annex-wanted EXPR` sets a git-annex preferred-content expression for the sibling, for
  example `standard` combined with a group, or `include=*.nii.gz`. `--annex-required`
  makes content mandatory there rather than merely wanted.
- `--pushurl` supplies a separate write URL when the read URL cannot be pushed to, the
  usual case for an HTTPS read path with an SSH write path.
- `--as-common-datasrc NAME` configures a sibling "as a common data source of the dataset
  that can be automatically used by all consumers", which is how a public mirror becomes
  usable by anyone who clones without them configuring anything.
- `--inherit` takes configuration from the superdataset's corresponding sibling, which
  matters when publishing a nested dataset hierarchy.

## Creating siblings

Rather than configuring by hand, use the `create-sibling-*` family, which creates the
remote side and configures the local side together:

| Command | Target |
|---|---|
| `datalad create-sibling-github` | A GitHub repository |
| `datalad create-sibling-gitlab` | A GitLab project |
| `datalad create-sibling-gogs` / `-gin` / `-gitea` | GOGS, GIN, and Gitea instances |
| `datalad create-sibling-ria` | A RIA store |
| `datalad create-sibling` | A generic sibling over SSH |

GIN is worth knowing about in a neuroscience context because it hosts annexed content
directly, which collapses the two-target model back into one target.

## RIA stores

A RIA store is a flat, filesystem-level layout for holding many datasets, designed for
cluster and institutional storage where per-dataset repositories are impractical. Clone
URLs use a `ria+` prefix and a fragment identifying the dataset:

```bash
datalad clone ria+ssh://[user@]hostname/absolute/path/to/ria-store#<dataset-id>
datalad clone ria+file:///home/me/myriastore#e3e70682-c209-4cac-629f-6fbed82c07cd
datalad clone ria+file://$HOME/myriastore#~dl-101
```

The fragment is either the full dataset ID or an alias prefixed with `~`. Aliases exist
because dataset IDs are UUIDs and nobody remembers them.

```bash
datalad create-sibling-ria -s ria-backup --alias dl-101 --new-store-ok \
  "ria+file:///home/me/myriastore"
```

- `--new-store-ok` permits creating the store when it does not already exist. Without it,
  pointing at a nonexistent path is an error rather than a silent creation.
- `--alias` sets the friendly name used in the clone fragment.
- `--storage-sibling` controls the git-annex special remote. `off` disables it, and `only`
  creates the special remote without the regular RIA sibling.
- `--shared` sets multi-user permissions using the values `git init --shared` accepts.

By default the command creates both a regular sibling and a storage sibling named with a
`-storage` suffix.

## Pushing

```
datalad push [-h] [-d DATASET] [--to SIBLING] [--since SINCE] [--data
    {anything|nothing|auto|auto-if-wanted}] [-f
    {all|gitpush|checkdatapresent}] [-r] [-R LEVELS] [-J NJOBS]
    [--version] [PATH ...]
```

`--data` controls annexed content transfer, and the default is `auto-if-wanted`:

| Value | Behaviour |
|---|---|
| `anything` | Transfer all annexed content |
| `nothing` | Skip `git annex copy` entirely, publishing history only |
| `auto` | Use `git annex copy --auto`, so preferred-content settings decide |
| `auto-if-wanted` | Default. Use auto mode only when wanted settings exist on the remote |

The default is the reason a push can succeed while transferring no data: with no
preferred-content configuration on the target, `auto-if-wanted` has nothing to act on.
When a collaborator reports that `get` fails after you pushed, check this before anything
else, and push again with `--data anything`.

`--since SINCE` limits what is considered, and `--since '^'` uses the last known state of
the sibling's branch as the baseline. `-f/--force` accepts `gitpush` (override Git push
safety), `checkdatapresent` (skip the git-annex copy optimisation and transfer regardless
of what the remote is believed to hold), or `all`.

A complete first publication:

```bash
datalad create-sibling-github myaccount/mydataset
datalad siblings add -s store --url s3://my-bucket/mydataset
datalad siblings configure -s github --publish-depends store
datalad push --to github --data anything -r
```

Verify from the other side rather than trusting the push output:

```bash
datalad clone https://github.com/myaccount/mydataset.git /tmp/verify
datalad get -d /tmp/verify <a representative file>
```

## Credentials

DataLad resolves credentials in a defined order and stores interactively entered secrets
through the `keyring` package, using whichever backend that package finds on the system.

Three ways to supply them, in increasing order of automation:

1. **Interactive.** DataLad prompts when a credential is needed and not available, and
   stores the answer in the active keyring backend.
2. **Configuration.** A configuration item `datalad.credential.<name>.<component>` set at
   any DataLad configuration level.
3. **Environment.** "Variable names take the form of `DATALAD_CREDENTIAL_<NAME>_<COMPONENT>`,
   and standard replacement rules into configuration variable names apply." The
   transformation replaces `__` with a hyphen, then `_` with a dot, then lowercases. Keep
   credential names simple and free of underscores so this stays predictable.

Setting `datalad.credentials.force-ask` forces interactive re-entry, overriding a stored
credential with a new value. That is the fix when a rotated key keeps failing because the
old one is still cached.

For git-annex special remotes on a fresh clone, the credential is not enough on its own.
The special remote also has to be enabled locally:

```bash
datalad siblings -d . enable -s store
# or, at the git-annex level
git annex enableremote store
```

A clone that can reach the Git history but reports no available source for content is
usually a special remote that was never enabled, not a missing credential. Check
`git annex info` for the remote's status before assuming an authentication problem.

Never commit credentials into the dataset. The whole point of the dataset is that it gets
published, and a secret in the history is published with it.
