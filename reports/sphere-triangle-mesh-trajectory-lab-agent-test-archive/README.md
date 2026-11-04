# Original test output archive

The original agent temporary directories use private Windows ACLs, so Git running as the user could not read them during the first feature commit. All 13 files were copied byte for byte into this normal workspace directory; the originals remain untouched locally. `archive.json` lists original paths, archived paths, exact byte sizes and SHA-256 hashes.

These are the actual command records and stdout/stderr, including the first 18/19 failure and subsequent 19/19 and 20/20 successes. The summary's original paths resolve through this manifest for repository readers. No missing output was recreated.
