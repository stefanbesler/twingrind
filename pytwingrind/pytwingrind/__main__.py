import sys
import logging
from argparse import ArgumentParser

prepare_parser = ArgumentParser("""Prepares the source code of a PLC
so that is can be used with Twingrind. The script parses through all source files (*.POU)
and adds boilerplate code to every functionblock, function and method in the PLC.

The output of this command is a hashmap, which is a mapping between a uniquely generated id and
the functionblock-, function- or methodname, respectively. The hashmap file has to be provided when
reconstructiong the call-graph.
""")
prepare_parser.add_argument("-d", "--directory", help="Directory containing the PLC project and all source files", required=True)
prepare_parser.add_argument("-m", "--hashmap", help="Filepath of a hashmap, if the file does not exist, it will be created", required=True)
    
fetch_parser = ArgumentParser("""Reads out all call-graph caputues from a PLC""")
fetch_parser.add_argument("-n", "--netid", help="AMS-NetId of the target machine, defaults to the local machine", default="", required=False)
fetch_parser.add_argument("-p", "--port", help="Port of the PLC", default=851, required=False)
fetch_parser.add_argument("-d", "--directory", help="Output directory", default="./", required=False)
fetch_parser.add_argument("-o", "--outputname", help="Outputname prefix for files that are generated", default="callstack", required=False)
fetch_parser.add_argument("-N", "--namespace", help="Namespace that is used for the Twingrind library, useful if used with TC_SYM_WITH_NAMESPACE", default="Twingrind", required=False)
fetch_parser.add_argument("-r", "--reset", help="Reset the profiler, this action is taken before taken new shots using the shots argument", action='store_true')
fetch_parser.add_argument("-s", "--shots", help="How many single shots should be taken when calling the fetch command", default=0, required=False, type=int)

reconstruct_parser = ArgumentParser("""Converts a callstack, as it has been read of the fetch command together with the
hashmap that has been created for the PLC with the prepare command, to the callgrind format.""")
reconstruct_parser.add_argument("-m", "--hashmap", help="Hashmap that is created with the prepare command", required=True)
reconstruct_parser.add_argument("-c", "--callstack", help="Callstack that was read out with the fetch command", required=True)
reconstruct_parser.add_argument("-d", "--directory", help="Output directory", default="./", required=False)
reconstruct_parser.add_argument("-q", "--masquarade", help="Obfuscate names of functionblocks, functions and methods", action="store_true", required=False) 
reconstruct_parser.add_argument("-o", "--outputname", help="Outputname prefix for files that are generated", default="callstack", required=False)
reconstruct_parser.add_argument("-R", "--recursion-limit", help="Set pythons maximum recursion limit", default=2000, required=False)

process_parser = ArgumentParser("""Fetches all captures from the PLC and then reconstructs the call-graph. This command
is the same as running fetch and then reconstructing every callstack""")
process_parser.add_argument("-n", "--netid", help="AMS-NetId of the target machine, defaults to the local machine", default="", required=False)
process_parser.add_argument("-p", "--port", help="Port of the PLC", default=851, required=False)
process_parser.add_argument("-d", "--directory", help="Output directory", default="./", required=False)
process_parser.add_argument("-m", "--hashmap", help="Hashmap that is created with the prepare command", required=True)
process_parser.add_argument("-q", "--masquarade", help="Obfuscate names of functionblocks, functions and methods", action="store_true", required=False) 
process_parser.add_argument("-o", "--outputname", help="Outputname prefix for files that are generated", default="callstack", required=False)
process_parser.add_argument("-N", "--namespace", help="Namespace that is used for the Twingrind library, useful if used with TC_SYM_WITH_NAMESPACE", default="Twingrind", required=False)
process_parser.add_argument("-r", "--reset", help="Reset the profiler, this action is taken before taken new shots using the shots argument", action='store_true')
process_parser.add_argument("-s", "--shots", help="How many single shots should be taken when calling the fetch command", default=0, required=False, type=int)
process_parser.add_argument("-R", "--recursion-limit", help="Set pythons maximum recursion limit", default=2000, required=False)

clean_parser = ArgumentParser("""Removes all boilerplate code that has been added the PLC with the prepare command.
Use this command if profiling is no longer needed.
""")
clean_parser.add_argument("-d", "--directory", help="Directory containing the PLC project and all source files", required=True)

def main():
  logging.basicConfig(level=logging.DEBUG)
  cmds = ["prepare", "fetch", "reconstruct", "process", "clean"]
  if len(sys.argv) <= 1 or sys.argv[1] not in cmds:
    logging.error(f"""Invalid command. The first arugment must be one of the following items {cmds}""")
    sys.exit(-1)
    
  arg = sys.argv[1]
  if arg == "prepare":
    import pytwingrind.prepare

    parser = prepare_parser
    args = vars(parser.parse_args(sys.argv[2::]))
    pytwingrind.prepare.run(args["directory"], args["hashmap"])
  
  elif arg == "fetch":
    import pytwingrind.fetch

    parser = fetch_parser
    args = vars(parser.parse_args(sys.argv[2::]))
    pytwingrind.fetch.run(args["netid"], int(args["port"]), args["directory"], args["outputname"], args["namespace"], args["reset"], args["shots"])

  elif arg == "reconstruct":
    import pytwingrind.reconstruct

    parser = reconstruct_parser
    args = vars(parser.parse_args(sys.argv[2::]))
    sys.setrecursionlimit(int(args["recursion_limit"]))
    pytwingrind.reconstruct.run(args["hashmap"], args["callstack"], args["directory"], args["outputname"])
 
  elif arg == "process":
    import pytwingrind.fetch
    import pytwingrind.reconstruct

    parser = process_parser
    args = vars(parser.parse_args(sys.argv[2::]))
    sys.setrecursionlimit(int(args["recursion_limit"]))
    callstacks = pytwingrind.fetch.run(args["netid"], int(args["port"]), args["directory"], args["outputname"], args["namespace"], args["reset"], args["shots"])
    
    for callstack in callstacks:
      pytwingrind.reconstruct.run(args["hashmap"], callstack, args["directory"], "")
    
  elif arg == "clean":
    import pytwingrind.clean

    parser = clean_parser
    args = vars(parser.parse_args(sys.argv[2::]))
    pytwingrind.clean.run(args["directory"])
