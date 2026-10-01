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

| Command                                           | Target                          |
| ------------------------------------------------- | ------------------------------- |
| `datalad create-sibling-github`                   | A GitHub repository             |
| `datalad create-sibling-gitlab`                   | A GitLab project                |
| `datalad create-sibling-gogs` / `-gin` / `-gitea` | GOGS, GIN, and Gitea instances  |
| `datalad create-sibling-ria`                      | A RIA store                     |
| `datalad create-sibling`                          | A generic sibling over SSH      |

The `create-sibling-*` family covers *Git* siblings (a Git remote plus a hosting-service
repository or project) and the RIA layout, which packages a Git remote and a matching
git-annex special remote together. Storage-only targets — S3 buckets, WebDAV, plain SSH
directories, rclone-reachable services — are git-annex *special remotes* rather than Git
remotes, and they are created with `git annex initremote` rather than `create-sibling-*`.
That distinction is what the two-target model turns on: the Git sibling carries history,
the storage sibling carries content. RIA stores, GIN, and suitable filesystem/SSH
Git-annex repositories can serve both from one infrastructure location.

GIN is worth knowing about in a neuroscience context because it hosts annexed content
directly, which collapses the two-target model back into one target.

## RIA stores

A RIA store is a flat, filesystem-level layout for holding many datasets, designed for
cluster and institutional storage where per-dataset repositories are impractical. Clone
URLs use a `ria+` prefix and a fragment identifying the dataset:

```bash
datalad clone "ria+ssh://user@hostname/absolute/path/to/ria-store#DATASET-UUID"
datalad clone "ria+file://${HOME}/myriastore#~dl-101"
```

The fragment is either the full dataset ID or an alias prefixed with `~`. Aliases exist
because dataset IDs are UUIDs and nobody remembers them.

```bash
datalad create-sibling-ria -s ria-backup --alias dl-101 --new-store-ok \
  "ria+file://${HOME}/myriastore"
```

- `--new-store-ok` permits creating the store when it does not already exist. Without it,
  pointing at a nonexistent path is an error rather than a silent creation.
- `--alias` sets the friendly name used in the clone fragment.
- `--storage-sibling` controls the git-annex special remote. `off` disables it, and `only`
  creates the special remote without the regular RIA sibling.
- `--shared` sets multi-user permissions using the values `git init --shared` accepts.

By default the command creates both a regular sibling and a storage sibling named with a
`-storage` suffix and sets their publication dependency. RIA HTTP(S) access is read-only;
provide an SSH/file `--push-url` for writes. Quote RIA URLs so shell `#`, `~`, and bracket
interpretation cannot change them. Do not run ordinary git-annex commands directly
inside a RIA store; access its special layout through the ORA remote.

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
| `anything` | Transfer selected current annexed content without preferred-content filtering |
| `nothing` | Skip `git annex copy` entirely, publishing history only |
| `auto` | Let wanted expressions and required copy counts select transfers |
| `auto-if-wanted` | Default. Apply auto mode when wanted is configured; otherwise behave as `anything` |

Without a wanted expression, the default does transfer selected content; it is not a
history-only push. All modes are bounded by selected paths/current revision and local
content availability. A push is not an archive of every historical key. If later `get`
fails, inspect transfer results, missing local bytes, remote access, and wanted filters.
A tiny directory-special-remote test verifies this default behavior.

`--since SINCE` limits what is considered, and `--since '^'` uses the last known state of
the sibling's branch as the baseline. `-f/--force` accepts `gitpush` (override Git push
safety), `checkdatapresent` (skip the git-annex copy optimisation and transfer regardless
of what the remote is believed to hold), or `all`.

Illustrative authenticated first publication (creates GitHub/S3 resources; not run in
this refresh). Use a bare repository name for the authenticated user; a prefix such as
`myorg/` means an organization, not a personal account:

```bash
datalad create-sibling-github mydataset
git annex initremote store type=S3 bucket=my-bucket protocol=https \
  encryption=none autoenable=true
datalad siblings configure -s github --publish-depends store
datalad push --to github --data anything -r
```

The Git sibling is created by `datalad create-sibling-github`, the storage sibling by
`git annex initremote`; see the note under "Creating siblings" above for why the two
are not the same tool. `autoenable=true` lets a fresh clone reach the storage sibling
without a manual `enableremote` step when its other requirements are met. It does not
grant bucket access. `encryption=none` disables git-annex encryption; it does not make
an S3 bucket public. Configure access policy separately. For intended anonymous
downloads, set the special remote's `publicurl` to the reachable bucket/object URL and
verify it from an unauthenticated clone. Do not use the deprecated S3 `public` ACL
option for modern buckets. Private access and encryption are separate choices.

Verify from the other side rather than trusting the push output:

```bash
datalad clone https://github.com/myaccount/mydataset.git /tmp/verify
datalad get -d /tmp/verify path/to/representative-file
```

## Credentials

DataLad resolves credentials in a defined order and stores interactively entered secrets
through the `keyring` package, using whichever backend that package finds on the system.
Configuration (including environment overrides) is checked before keyring lookup;
interactive prompting is a fallback. Review the active backend on headless hosts.

Three ways to supply them, in increasing order of automation:

1. **Interactive.** DataLad prompts when a credential is needed and not available, and
   stores the answer in the active keyring backend.
2. **Local configuration.** `datalad.credential.<name>.<component>` can supply a
   component, but keep secrets out of tracked `.datalad/config` and shared config files.
   Prefer a suitable keyring or process environment for credentials.
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

A clone that reads Git history but cannot get content may have a disabled remote,
missing credentials, an inaccessible URL, or unpublished content. Check `git annex info`
and the transfer error to distinguish them. DataLad credentials do not automatically
configure every git-annex backend: the S3 special remote reads `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, and optionally `AWS_SESSION_TOKEN` during initialization or
enabling. Keep `embedcreds` disabled unless its sharing/encryption behavior is intended.

Official contracts: [push](https://docs.datalad.org/en/stable/generated/man/datalad-push.html),
[GitHub sibling](https://docs.datalad.org/en/stable/generated/man/datalad-create-sibling-github.html),
[RIA](https://docs.datalad.org/en/stable/generated/man/datalad-create-sibling-ria.html),
[S3 special remote](https://git-annex.branchable.com/special_remotes/S3/), and
[credentials](https://docs.datalad.org/en/stable/design/credentials.html).

Never commit credentials into the dataset. The whole point of the dataset is that it gets
published, and a secret in the history is published with it.
