# tc3profiler

For now Twincat 3 doesn't offer a profiling mechanism. The scripts, implemented within the scope of this repository, aim to add
such functionality in a relative simple way.
The scope of the project aim to add profiling of methods (of function blocks), rather than directly to function blocks. Coming from OOP we hardly use function blocks directly in our code base. 
Also, we focus on profiles of 1 cycle rather than profiling over a given timespan.

Currently this is work in progress, but the general idea is as follows

1. provide a simple profiler-library anyone can add to their application (not started)
2. add function calls that are used for stack reconstruction for all methods in a given application. ( > profiler_guards.py )
3. provide a script that triggers a profile measurement and then reads the callstack via ADS. The callstack is then stored on disk for later usage (not started)
4. provide a script that reads a callstack (created by 3.) from disk and converts it to the callgrind profile format, version 1 (http://kcachegrind.sourceforge.net/html/CallgrindFormat.html)

The profile can then be visualized by qcachegrind.
