# prechub Release Path Check

Catch filenames that work side by side on Linux but collide when a release is unpacked on a case-insensitive or Unicode-normalizing filesystem. For example, `Art/Hero.png` and `art/hero.png` can collide at both directory and file level.

The action checks tracked paths in the current Git index, including directory aliases and file/directory conflicts. It runs locally on the runner, reads filenames only and requires no token or external service. Case comparison uses JavaScript lowercase and Unicode NFC. Platform-specific naming rules can differ. Git filenames must be valid UTF-8. Untracked and ignored files, archive contents, and files inside submodules are outside the scan.

```yaml
name: Check release paths
on: [push, pull_request]
permissions:
  contents: read
jobs:
  paths:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hyukachu-code/prechub-release-path-check@v1.0.0
        id: paths
      - uses: actions/upload-artifact@v4
        if: always() && steps.paths.outputs.report != ''
        with:
          name: release-path-report
          path: ${{ steps.paths.outputs.report }}
```

Set `fail_on_collision: 'false'` to create a report without failing the job on a finding. The `collisions` output counts distinct pairs of paths. The `report` output gives the location of the JSON report on the runner. Filenames are recorded in the report. The upload step is optional.

For a packaged file list, Windows reserved names, duplicate archive entries, or paths outside the package root, use [Build Path Audit on Apify](https://apify.com/prechub/build-path-audit) or the [offline edition on itch.io](https://prechub.itch.io/build-path-audit). Both are paid options.

For teams using a hosted API, the [optional Python quickstart](examples/rapidapi/README.md) includes a standalone client, local request validation and CI exit codes. Its default run makes no network request. An explicit `--send` uses your own [RapidAPI subscription](https://rapidapi.com/hyukachucode/api/build-path-audit), which may incur usage charges. The GitHub Action above continues to run locally without that subscription.
