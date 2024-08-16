# verify_md5deep.py

This script is useful for verifying that the distro that an operator has sent
has not been damaged during transit to the server.

Sometimes the operator will include an md5deep file within the cruise data folder in incoming/r2r. If this is the case then you must perform a check to ensure that the contents of the data directory match what’s specified in the md5deep file. To do this run this md5deep command to generate your own md5 deep file. First you want to navigate to the directory within which the distro is sitting. Then run the md5deep linux tool with the name of the distro as an argument.

Note: the verify_md5deep script will require the paths of the two md5deep files to match which means you have to be careful when generating your md5deep. First check the distro md5deep and then make sure that, when you run the md5deep tool, the directories in your current directory match the root directorie of the distro md5 paths.


`md5deep -c -r -l -o f -t -z SKQ202313S > SKQ202313S.md5deep &`
Once this md5deep file is created (which may take a while) it is time to verify that the file hashes generated and stored in this md5deep file match the file hashes as recorded by the operator. To do this first cd into the same folder as the .md5deep file that was just created. Then run the verify_md5deep.py tool:



`verify_md5deep SKQ202408S.md5deep SKQ202408S_distro.md5deep -a > out 2>&1`
Note: verify_md5deep.py will be comparing only two fields of the .md5deep file. It will be comparing the checksum and the file path. Both of these must match in order for a file not to be flagged as different across files. This means that manual inspection of both md5deep files should be performed to ensure that the file paths will match. Often the root of the file path will need to be modified with a vim “search & replace” in order to get one .md5deep to match the other. One example replacement would be :%s/,\.\//&SR2324\//g which replaces ,./ with ,./SR2323/.

The first argument is the path to the md5deep file that you just created and the second argument is the path to the operator-supplied md5deep file.


