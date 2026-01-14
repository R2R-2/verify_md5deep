# verify_md5deep.py

## Overview
This script is useful for verifying that the distro that an operator has sent
has not been damaged during transit to the server.

Sometimes the operator will include an md5deep file within the cruise data folder in incoming/r2r. If this is the case then you must perform a check to ensure that the contents of the data directory match what’s specified in the md5deep file. To do this run this md5deep command to generate your own md5 deep file. First you want to navigate to the directory within which the distro is sitting. Then run the md5deep linux tool with the name of the distro as an argument.

Note: the verify_md5deep script will allow the roots of the paths of files across the two md5deep files to vary slightly (by 3 root paths to be exact) the starts of the paths don't have to align exactly for matches to be made.

## Required packages
None! (yet)

## Generating a local copy of md5deep file
Run: `md5deep -c -r -l -o f -t -z SKQ202313S > SKQ202313S.md5deep &`

Once this md5deep file is created (which may take a while) it is time to verify that the file hashes generated and stored in this md5deep file match the file hashes as recorded by the operator. To do this first cd into the same folder as the .md5deep file that was just created. Then run the verify_md5deep.py tool:

## Using this tool
```
usage: verify_md5deep.py [-h] [-c num] [--ignore-hashes] [--ignore-paths] [--exclude-path-list pattern [pattern ...]] [--include-path-list pattern [pattern ...]]
                         [--show-excluded-pairs]
                         file1 file2

Compare two md5deep file listing files

positional arguments:
  file1                 md5deep file listing file 1
  file2                 md5deep file listing file 2

optional arguments:
  -h, --help            show this help message and exit
  -c num                copy diff of files in a given direction (1 or 2)
  --ignore-hashes       don't compare hashes
  --ignore-paths        don't compare filepaths
  --exclude-path-list pattern [pattern ...]
                        list of regexes where if a filepath matches any of them it is not included in the comparisons.
  --include-path-list pattern [pattern ...]
                        list of regexes where a filepath must match at least one to be included in the comparisons.
  --show-excluded-pairs
                        show all of the pairs that were not compared along with their reason for exclusion
```