"""
Author: Bart Meyers
Date: October 2012
Modification to 16bit/16bit datapath: September 2013

usage: python Test.py option <file_to_compile.txt> <file_to_test.circ>
         options:
             -a     :   test alu
             -s     :   test simple datapath (only r-type and sw/lw)
             -f     :   test full datapath (all instructions)

Needs to be in the same folder as logisim-generic-2.7.1.jar

This program will convert test cases (currently only ALU tests) to logisim dat files,
which can be loaded into your logisim project. If this project includes the main circuit
of ALU_GroupXX.circ, running this program with the project as last argument will behave 
as a test run: logisim will read in a test and oracle, and produce outputs for each test.
Then, this program will parse this output and verify whether the test result is the same
as the oracle.
"""

logisim = "logisim-generic-2.7.1.jar" # logisim filename

def dec2twoscompl_hex(s, width):
    if s.startswith("-"):
        return "%x" % ((2**width)+int(s))
    elif len(s) == width: # in case of a binary string
        return "%x" % int(s, 2)
    else:
        return "%x" % int(s)

def twoscompl_bin2dec(s, width):
    return (int(s.replace(" ", ""), 2)-2**width) if s[0] == '1' else int(s.replace(" ", ""), 2)

def findallfiles(path, pattern, subfolders=True): # find all files in path whose file matches a given pattern
    import re, os
    def match(pattern, f):
        return re.match(pattern, f) and not f.startswith(".")
    goodfiles = []
    if subfolders:
        for r,d,files in os.walk(path):
            for f in files:
                if match(pattern, f):
                    goodfiles.append(os.path.join(r,f))
    else:
        files = os.listdir(path)
        r = path
        for f in files:
            if match(pattern, f):
                 goodfiles.append(os.path.join(r,f))
    return goodfiles

def Datapathtestcompiler(textfile, testfile, width, nr_of_tests, fulldatapath=True):
    import re, os
    def pattern(patterns, can_have_label=False):
        fullpattern = r'^\s*' # pattern must start in the beginning of a line
        if can_have_label:
            fullpattern += "(?P<label>(%s:\s)?)" % labelpattern()
            fullpattern += r'\s*'
        for key, value in patterns:
            fullpattern += "(?P<%s>%s)" % (key, value) # then, add the patterns
            fullpattern += r'\s+'
        fullpattern += "(?P<comment>(#.*)?)$" # a comment might be added at the end of the line
        return re.compile(fullpattern)
    # some conversions
    def int2bin(s, width): # convert a signed integer to a two's complement bin notation
        if (int(s) > 2**(width-1)-1 or int(s) < -(2**(width-1))):
            raise ValueError("Number %s exceeds supported range of [%d, %d]" % (s, -(2**(width-1)), 2**(width-1)-1))
        else:
            return bin(int(s))[2:].rjust(width, "0") if not s.startswith("-") else bin((2**width)+int(s))[2:]
    def uint2bin(s, width): # convert a positive integer to a bin notation (can be two's complement or not - same notation)
        if (int(s) > 2**(width)-1 or int(s) < 0):
            raise ValueError("Number %s exceeds supported range of [%d, %d]" % (s, 0, 2**(width)-1))
        else: # only positive number
            return bin(int(s))[2:].rjust(width, "0")
    def reg2bin(s, width): # convert a register string to a bin notation (width bits)
        return uint2bin(s.lstrip('r').lstrip('$r'), width)
    def label2bin(s, width, symboltable, count_from=None): # convert a label to a binary jump value (by looking in the symboltable), if count_from (int) than jump relative to that memory address
        if count_from is None:
            return int2bin(str(symboltable[s]), width)
        else:
            return int2bin(str(symboltable[s] - count_from - 1), width)
    def ubin2hex(s, width): # convert a binary number to a hexadecimal number
        if len(s) != width:
            raise ValueError("Binary number %s should be width %d, but is width %d" % (s, width, len(s)))
        else:
            return "%x" % int(s, 2)
    # some patterns for matching numbers
    def integerpattern():
        return r'[+-]?\d+'
    def uintegerpattern():
        return r'\+?\d+'
    def binarypattern(n):
        return r'[01]{%d}' % n
    def register(): # 16 registers
        return r'r(\d|10|11|12|13|14|15)'
    def writeregister(): # 16 registers
        return r'r[1|2|3|4|5|6|7|8|9|10|11|12|13|14|15]'
    def labelpattern():
        return r'[a-zA-Z_]\w*'
    # all operations
    loadmem = pattern((('mode', 'LOADMEM'),))
    datamem = pattern((('mode', 'DATAMEM'),))
    checkmem = pattern((('mode', 'CHECKMEM'),))
    end = pattern((('mode', 'END'),))
    checkline1 = pattern((('reg', register()+r'\s*:'), ('value', binarypattern(16))))
    checkline2 = pattern((('reg', register()+r'\s*:'), ('value', integerpattern())))
    checkline3 = pattern((('reg', r'pc\s*:'), ('value', binarypattern(16))))
    checkline4 = pattern((('reg', r'pc\s*:'), ('value', integerpattern())))
    valueline = pattern((('imm', integerpattern()),))
    bvalueline = pattern((('imm', binarypattern(width)),))
    labeldecl = pattern((('label', labelpattern()+":"), ('remainder', r'.*')))
    skipline = pattern([])
    # the following are operations of 16-bit words, on a register file of 16 registers (r0 is zero, r15 is reserved as ra)
    operations = [
    ('zero' , pattern((('op', 'zero'), ('rd', register())), can_have_label=True),                                                       "zero rd            -->  rd := 0",                     lambda m, params : '0000'+str(reg2bin(m.group('rd'),4))+'00000000' ),
    ('and'  , pattern((('op', 'and'),  ('rd', register()), ('rs', register()), ('rt', register())), can_have_label=True),               "and rd rs rt       -->  rd := rs&rt",                 lambda m, params : '0001'+str(reg2bin(m.group('rd'),4))+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4)) ),
    ('or'   , pattern((('op', 'or'),   ('rd', register()), ('rs', register()), ('rt', register())), can_have_label=True),               "or rd rs rt        -->  rd := rs|rt",                 lambda m, params : '0010'+str(reg2bin(m.group('rd'),4))+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4)) ),
    ('not'  , pattern((('op', 'not'),  ('rd', register()), ('rs', register())), can_have_label=True),                                   "not rd rs          -->  rd := !rs",                   lambda m, params : '0011'+str(reg2bin(m.group('rd'),4))+str(reg2bin(m.group('rs'),4))+"0000" ),
    ('add'  , pattern((('op', 'add'),  ('rd', register()), ('rs', register()), ('rt', register())), can_have_label=True),               "add rd rs rt       -->  rd := rs+rt",                 lambda m, params : '0100'+str(reg2bin(m.group('rd'),4))+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4)) ),
    ('inv'  , pattern((('op', 'inv'),  ('rd', register()), ('rs', register())), can_have_label=True),                                   "inv rd rs          -->  rd := -rs",                   lambda m, params : '0101'+str(reg2bin(m.group('rd'),4))+str(reg2bin(m.group('rs'),4))+'0000' ),
    ('lt'   , pattern((('op', 'lt'),   ('rd', register()), ('rs', register()), ('rt', register())), can_have_label=True),               "lt rd rs rt        -->  rs<rt ? rd := 1 : rd := 0",   lambda m, params : '0110'+str(reg2bin(m.group('rd'),4))+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4)) ),
    ('gt'   , pattern((('op', 'gt'),   ('rd', register()), ('rs', register()), ('rt', register())), can_have_label=True),               "gt rd rs rt        -->  rs>rt ? rd := 1 : rd := 0",   lambda m, params : '0111'+str(reg2bin(m.group('rd'),4))+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4)) ),
    ('eq'   , pattern((('op', 'eq'),   ('rd', register()), ('rs', register()), ('rt', register())), can_have_label=True),               "eq rd rs rt        -->  rs=rt ? rd := 1 : rd := 0",   lambda m, params : '1000'+str(reg2bin(m.group('rd'),4))+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4)) ),
    ('lw'   , pattern((('op', 'lw'),   ('rs', register()), ('rt', register()), ('uimm', uintegerpattern())), can_have_label=True),      "lw rs rt uimm      -->  rt := MEM[rs+uimm]",          lambda m, params : '1110'+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4))+str(uint2bin(m.group('uimm'),4)) ),
    ('sw'   , pattern((('op', 'sw'),   ('rs', register()), ('rt', register()), ('uimm', uintegerpattern())), can_have_label=True),      "sw rs rt uimm      -->  MEM[rs+uimm] := rt",          lambda m, params : '1111'+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4))+str(uint2bin(m.group('uimm'),4)) )
    ]
    if fulldatapath: operations += [
    ('jal'  , pattern((('op', 'jal'),  ('addr', binarypattern(12))), can_have_label=True),                                              "jal addr        -->  r15 := pc+1 ; pc := addr",    lambda m, params : '1001'+m.group('addr') ),
    ('jal'  , pattern((('op', 'jal'),  ('addr', uintegerpattern())), can_have_label=True),                                              "jal addr        -->  r15 := pc+1 ; pc := addr",    lambda m, params : '1001'+str(uint2bin(m.group('addr'),12)) ),
    ('jal'  , pattern((('op', 'jal'),  ('to', labelpattern())), can_have_label=True),                                                   "jal addr        -->  r15 := pc+1 ; pc := addr",    lambda m, params : '1001'+str(label2bin(m.group('to'),12,params[1])) ),
    ('ori'  , pattern((('op', 'ori'),  ('rs', register()), ('uimm', binarypattern(8))), can_have_label=True),                           "ori rs uimm     -->  rs := rs|uimm",               lambda m, params : '1010'+str(reg2bin(m.group('rs'),4))+m.group('uimm') ),
    ('ori'  , pattern((('op', 'ori'),  ('rs', register()), ('uimm', uintegerpattern())), can_have_label=True),                          "ori rs uimm     -->  rs := rs|uimm",               lambda m, params : '1010'+str(reg2bin(m.group('rs'),4))+str(uint2bin(m.group('uimm'),8)) ),
    ('lui'  , pattern((('op', 'lui'),  ('rs', register()), ('uimm', binarypattern(8))), can_have_label=True),                           "lui rs uimm     -->  rs := uimm<<8",               lambda m, params : '1011'+str(reg2bin(m.group('rs'),4))+m.group('uimm') ),
    ('lui'  , pattern((('op', 'lui'),  ('rs', register()), ('uimm', uintegerpattern())), can_have_label=True),                          "lui rs uimm     -->  rs := uimm<<8",               lambda m, params : '1011'+str(reg2bin(m.group('rs'),4))+str(uint2bin(m.group('uimm'),8)) ),
    ('jr'   , pattern((('op', 'jr'),   ('rs', register()), ('imm', binarypattern(8))), can_have_label=True),                            "jr rs imm       -->  pc := rs+imm",                lambda m, params : '1100'+str(reg2bin(m.group('rs'),4))+m.group('imm') ),
    ('jr'   , pattern((('op', 'jr'),   ('rs', register()), ('imm', integerpattern())), can_have_label=True),                            "jr rs imm       -->  pc := rs+imm",                lambda m, params : '1100'+str(reg2bin(m.group('rs'),4))+str(int2bin(m.group('imm'),8)) ),
    ('jr'   , pattern((('op', 'jr'),   ('rs', register()), ('to', labelpattern())), can_have_label=True),                               "jr rs imm       -->  pc := rs+imm",                lambda m, params : '1100'+str(reg2bin(m.group('rs'),4))+str(label2bin(m.group('to'),8,params[1])) ),
    ('bne'  , pattern((('op', 'bne'),  ('rs', register()), ('rt', register()), ('imm', integerpattern())), can_have_label=True),        "bne rs rt imm   -->  rs!=rt ? pc := pc+1+imm",     lambda m, params : '1101'+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4))+str(int2bin(m.group('imm'),4)) ),
    ('bne'  , pattern((('op', 'bne'),  ('rs', register()), ('rt', register()), ('to', labelpattern())), can_have_label=True),           "bne rs rt imm   -->  rs!=rt ? pc := pc+1+imm",     lambda m, params : '1101'+str(reg2bin(m.group('rs'),4))+str(reg2bin(m.group('rt'),4))+str(label2bin(m.group('to'),4,params[1],params[0]-1)) ),
    ]
    
    # quick first parse pass: we want to put all labels in a symboltable
    symboltables = dict()
    f = open(textfile, 'r')
    mode = "idle"
    testnr = 0
    line = f.readline()
    while len(line) > 0:
        if not (line == "\n" or line == os.linesep or skipline.search(line)):
            if mode == "idle":
                if loadmem.search(line):
                    mode = "loadmem"
                    testnr += 1
                    curtestfile = testfile+str(testnr)
                    symboltables[curtestfile] = dict() # start a new test program, and a new debug trace
                    programlinenr = 0
            elif mode == "ignore":
                if loadmem.search(line): mode = "loadmem"
                elif end.search(line): mode = "idle"
            elif mode == "loadmem":
                if datamem.search(line): mode = "ignore"
                elif checkmem.search(line): mode = "ignore"
                elif end.search(line): mode = "idle"
                else:
                    m = labeldecl.search(line)
                    if m:
                        symboltables[curtestfile][m.group("label").strip().strip(":")] = programlinenr
                    programlinenr += 1
        line = f.readline()
    f.close()
  
    # second pass: parse content
    def process_constant(m):
        return int2bin(m.group('imm'), width)
    f = open(textfile, 'r')
    mode = "idle"
    debugtraces = dict()
    testnr = 0
    linenr = 1
    line = f.readline()
    while len(line) > 0:
        if not (line == "\n" or line == os.linesep or skipline.search(line)):
            if mode == "idle":
                if loadmem.search(line):
                    #print "change to loadmem"
                    mode = "loadmem"
                    testnr += 1
                    curtestfile = testfile+str(testnr)
                    debugtraces[curtestfile] = dict() # start a new test program, and a new debug trace
                    programlinenr = 0
            elif mode == "loadmem":
                matched = None
                matcheddesc = None
                if datamem.search(line):
                    if programlinenr == 0:
                        print("warning: line %d: wanted to start a data section, but expects instructions first" % linenr)
                    programlinenr += 1
                    debugtraces[curtestfile][programlinenr] = {"linenr": linenr, "line": "STOP", "bin": "0"*width, "hex": ubin2hex("0"*width, width), "name": "STOP", "checks": dict()}
                    #print "change to datamem"
                    mode = "datamem"
                elif checkmem.search(line):
                    if programlinenr == 0:
                        print("warning: line %d: wanted to start a check section, but expects instructions first" % linenr)
                    #print "change to checkmem"
                    mode = "checkmem"
                elif end.search(line):
                    #print "change to idle"
                    mode = "idle"
                else:
                    programlinenr += 1
                    # check whether the line contains an instruction
                    for opname, oppattern, opdescription, opparser in operations:
                        m = oppattern.search(line)
                        if m:
                            try:
                                binary = opparser(m, (programlinenr,symboltables[curtestfile]))
                                debugtraces[curtestfile][programlinenr] = {"linenr": linenr, "line": line.strip(), "bin": binary, "hex": ubin2hex(binary, width), "name": opname, "checks": dict()}
                            except Exception as e:
                                print("could not parse line %d:" % linenr, "'%s'" % line.strip(), e)
                            matched = opname
                            break
                        elif not matcheddesc: # check if line started with a certain operation identifier
                            if re.compile("^\\s*%s\s+" % opname).search(line):
                                matcheddesc = opdescription
                    if not matched:
                        print("line %d not recognized: '%s', but should be of the form: %s"  % (linenr, line.strip(), str(matcheddesc) if matcheddesc else ""))
            elif mode == "datamem":
                if end.search(line):
                    #print "change to idle"
                    mode = "idle"
                elif checkmem.search(line):
                    #print "change to checkmem"
                    mode = "checkmem"
                else:
                    programlinenr += 1
                    matched = None
                    for immpattern in [valueline, bvalueline]:
                        m = immpattern.search(line)
                        if m:
                            binary = process_constant(m)
                            debugtraces[curtestfile][programlinenr] = {"linenr": linenr, "line": line.strip(), "bin": binary, "hex": ubin2hex(binary, width), "name": "imm", "checks": dict()}
                            matched = "imm"
                            break
                    if not matched:
                        print("line %d not recognized: '%s', but should be %d-bit data"  % (linenr, line.strip(), width))
            elif mode == "checkmem": # insert a check after the last instruction
                if end.search(line):
                    #print "change to idle"
                    mode = "idle"
                elif loadmem.search(line):
                    if fulldatapath:
                        print("warning: when checking the full datapath, only checks at the end of the program will be made")
                    #print "change to loadmem"
                    mode = "loadmem"
                elif datamem.search(line):
                    #print "change to loadmem"
                    programlinenr += 1
                    debugtraces[curtestfile][programlinenr] = {"linenr": linenr, "line": "STOP", "bin": "0"*width, "hex": ubin2hex("0"*width, width), "name": "STOP", "checks": dict()}
                    mode = "datamem"
                else:
                    m = checkline1.search(line)
                    m = checkline2.search(line) if not m else m
                    m = checkline3.search(line) if not m else m
                    m = checkline4.search(line) if not m else m
                    if m:
                        #print "checkline"
                        if len(m.group("value")) == width:
                            binval = m.group("value")
                        else:
                            binval = str(int2bin(m.group("value"),width))
                        # now add check to last instruction (ignore all data fields)
                        i = programlinenr
                        lastop = debugtraces[curtestfile][i]
                        while lastop["name"] in ["imm", "STOP"]:
                            lastop = debugtraces[curtestfile][i]
                            i -= 1
                        lastop["checks"][0 if m.group("reg") == "pc:" else 1+int(m.group("reg").rstrip(":").lstrip("r"))] = binval
                    else:
                        print("line %d not recognized: '%s', but should be of the form: reg: value"  % (linenr, line.strip()))
        line = f.readline()
        #print "%12s   %s" % (mode, line.strip())
        #print "\n".join(["%s : %s" % (key, debugtraces[curtestfile][key]) for key in debugtraces[curtestfile].keys()])
        linenr += 1
    f.close()
    #print debugtraces
    
    # write all content to a raw data file
    import os.path
    for curtestfile in debugtraces.keys():
        debugtrace = debugtraces[curtestfile]
        f = open(curtestfile, 'w')
        f.write("v2.0 raw\n")
        traces = debugtraces[curtestfile].keys()
        traces = sorted(traces)
        for i in traces:
            f.write(debugtraces[curtestfile][i]["hex"])
            f.write("\n")
        f.close()

    print("all done: " + textfile)
    return debugtraces

def SimpleDatapathtestcompiler(textfile, testfile, width, nr_of_tests):
    return Datapathtestcompiler(textfile, testfile, width, nr_of_tests, fulldatapath=False)

def Datapathparser(reportfile, debugtrace, width, nr_of_tests, fulldatapath=True):
    #for k in debugtrace.keys(): print k, debugtrace[k]
    # display debug information
    try:
        f = open(reportfile, 'r')
    except IOError:
        print("filename %s not found" % reportfile)
        return False

    nr_of_tests = 0
    failures = 0
    errors = 0
    lines = f.readlines()
    instructionkeys = [line for line in debugtrace.keys() if not debugtrace[line]["name"] in ["STOP", "imm"]]
    if not fulldatapath and len(lines) <= len(instructionkeys) and len(debugtrace) > 0:
        print("LOGISIM ERROR: Simulation did not return good results - maybe your program loops infinitely on the datapath?\n-- Try executing your program in logisim by loading the generated test file in your RAM-elements and starting clock ticks.")
        return (0,0,0)
    f.close()
    
    # first check for any errors in output
    for i in range(len(lines)):
        line = lines[i]
        items = [item.replace(" ", "").strip() for item in line.split("\t")]
        regnr = -1
        for item in items:
            regname = "pc" if regnr == -1 else "r%d" % regnr
            regnr += 1
            if 'E' in item or 'x' in item:
                if not fulldatapath:
                    curtrace = debugtrace[i]
                    print("Warning: %s has value %s, at line %d: %s" % (regname, item, curtrace["linenr"], curtrace["line"]))
                else:
                    print("Warning: %s has value %s" % (regname, item))
    
    for i in range(1, len(instructionkeys)+1):
        curtrace = debugtrace[i]
        checks = debugtrace[i]["checks"]
        # then go over the checks if present
        if (len(checks) > 0) and (not fulldatapath or i == len(instructionkeys)): # only check last instruction in case of a full datapath, otherwise we're in trouble in case of a loop
            if not fulldatapath:
                line = lines[i]
            else:
                line = lines[-2]
            items = [item.replace(" ", "").strip() for item in line.split("\t")]
            for reg in checks.keys():
                nr_of_tests += 1
                oracle = checks[reg]
                value = items[reg]
                regname = "pc"
                if reg > 1: regname = "r%d" % (reg-1)
                if 'E' in value or 'x' in value:
                    errors += 1
                    print("Error: %s has value %s, at line %d: %s" % (regname, value, curtrace["linenr"], curtrace["line"]))
                elif oracle != value:
                    failures += 1
                    print("Failure: %s must be %s, but is %s, at line %d: %s" % (regname, oracle, value, curtrace["linenr"], curtrace["line"]))
                    
    return (nr_of_tests, errors, failures)

def SimpleDatapathparser(reportfile, debugtrace, width, nr_of_tests):
    return Datapathparser(reportfile, debugtrace, width, nr_of_tests, fulldatapath=False)


def ALUtestcompiler(textfile, testfile, width, nr_of_tests):
    # compiler for ALU tests

    # operations
    operations = ('zero', 'and', 'or', 'not', 'add', 'inv', 'lt', 'gt', 'eq')
    
    # read all content to a list
            
    filecontent = []
    debugtrace = dict()
    linenr = 0
    f = open(textfile, 'r')
    for line in f.readlines():
        params = line.split()
        newparams = []
        if len(params) == 0:
            # empty line, skip
            continue
        linenr +=1
        op = params[0].lower()
        if op in operations:
            newparams.append(str(operations.index(op)))
        else:
            print("Unable to parse, did not find valid operation %s: %s" % (str(operations), line))
            return False
        # some syntax checks of the parameters
        for param in params[1:4]:
            try:
                if not (len(param) == width): # if its not a binary string...
                    if (int(param) > 2**(width-1)-1 or int(param) < -(2**(width-1))):
                        print("Number exceeds supported ALU range of [%d, %d] on line %d: %s" % (-(2**(width-1)), 2**(width-1)-1, linenr, line))
                        return False
                else:
                    try:
                        dec2twoscompl_hex(param, width)
                    except Exception:
                        print("Expected a binary string, but got %s, on line: %s" % (param, line))
                        return False
            except Exception as e:
                print("Line does not have the right format: %s" % line)
                return False
        for param in params[4:]:
            try:
                if not int(param) in [0,1]:
                    print("Parameter denoting that there should/shouldn't be an error must be 1 or 0, but is %s in line %s" % (param, line))
                    return False
            except Exception:
                print("Parameter denoting that there should/shouldn't be an error must be 1 or 0, but is %s in line %s" % (param, line))
                return False
        # add all parameters
        newparams += [dec2twoscompl_hex(s, width) for s in params[1:]]
        while len(newparams) < 8:
            newparams.append('0')
        newline = "%s %s %s %s %s %s %s %s\n" % (newparams[0],newparams[1],newparams[2],newparams[3],newparams[4],newparams[5],newparams[6],newparams[7])
        filecontent.append(newline)
        debugtrace[linenr] = [line, newline]
        if linenr == nr_of_tests:
            print("MAXIMUM NUMBER OF TESTS (%d) REACHED! IGNORING FURTHER TESTS. (You can split up your tests over two test files.)" % nr_of_tests)
            break
        
    f.close()

    # write all content to a raw data file
    import os.path
    f = open(testfile, 'w')
    f.write("v2.0 raw\n")
    for line in filecontent:
        f.write(line)
    f.close()

    print("all done: " + textfile)
    return {testfile: debugtrace}
    

def ALUparser(reportfile, debugtrace, width, nr_of_tests):
    # display debug information
    try:
        f = open(reportfile, 'r')
    except IOError:
        print("filename %s not found" % reportfile)
        return False

    failures = 0
    errors = 0
    linenr = 0
    lines = f.readlines()
    while linenr <= len(debugtrace)-1:
        # FIXME: for some students the two following lines had to be switched/-1 deleted because failure messages got messed up... this is the original setup
        linenr += 1
        line = lines[linenr-1]
        #print(debugtrace[linenr][0], debugtrace[linenr][1], line, "--------")
        cells = line.split("\t")
        if 'E' in line or 'x' in line:
            errors += 1
            print("-- Test on line %d error" % linenr)
            #print line,
            #print debugtrace[linenr][1],
            if debugtrace[linenr][0].split()[0] == "zero":
                op = "Operation %s ('%s'), result is %s, error code is %s" % (cells[1], debugtrace[linenr][0].split()[0], cells[-4], cells[-2])
            elif debugtrace[linenr][0].split()[0] in ["inv", "not"]:
                op = "Operation %s ('%s') with operand %s (%s), result is %s, error code is %s" % (cells[1], debugtrace[linenr][0].split()[0], cells[2], debugtrace[linenr][0].split()[1], cells[-4], cells[-2])
            elif debugtrace[linenr][0].split()[0] in ["and", "or", "add", "lt", "gt", "eq"]:
                op = "Operation %s ('%s') with operands %s (%s) and %s (%s), result is %s, error code is %s" % (cells[1], debugtrace[linenr][0].split()[0], cells[2], debugtrace[linenr][0].split()[1], cells[3], debugtrace[linenr][0].split()[2], cells[-4], cells[-2])
            print("%s%s" % (str(debugtrace[linenr][0]), op))
            print("")
        elif int(cells[-1]) == 0:
            failures += 1
            print("-- Test on line %d failure" % linenr)
            #print line,
            #print debugtrace[linenr][1],
            if debugtrace[linenr][0].split()[0] == "zero":
                op = "Operation %s ('%s'), result is %s (%s)" % (cells[1], debugtrace[linenr][0].split()[0], cells[-4], twoscompl_bin2dec(cells[-4], width))
            elif debugtrace[linenr][0].split()[0] in ["inv", "not"]:
                op = "Operation %s ('%s') with operand %s (%s), result is %s (%s)" % (cells[1], debugtrace[linenr][0].split()[0], cells[2], debugtrace[linenr][0].split()[1], cells[-4], twoscompl_bin2dec(cells[-4], width))
            elif debugtrace[linenr][0].split()[0] in ["and", "or", "add", "lt", "gt", "eq"]:
                op = "Operation %s ('%s') with operands %s (%s) and %s (%s), result is %s (%s)" % (cells[1], debugtrace[linenr][0].split()[0], cells[2], debugtrace[linenr][0].split()[1], cells[3], debugtrace[linenr][0].split()[2], cells[-4], twoscompl_bin2dec(cells[-4], width))
            if int(cells[-2]) == 1:
                op += " yielded an EXCEPTION"
            if int(cells[-2]) != int(cells[-3]):
                print("%s%s" % (str(debugtrace[linenr][0]), op))
                print("Expected %s as exception signal, but got %s" % (cells[-3], cells[-2]))
            if int(cells[-3]) == 0 and cells[-4] != cells[-5]: # results are only compared when no error is raised (int(cells[-3]) == 0)
                print("%s%s" % (str(debugtrace[linenr][0]), op))
                print("Expected %s as result, but got %s" % (cells[-5], cells[-4]))
            print("")
    return (linenr, errors, failures)


def Test(textfile, circfile, compiler, parser, logisim="logisim-generic-2.7.1.jar"):
    import sys, os, re
    width = 16 # width of one word
    nr_of_tests = 2**12
    
    if not os.path.isfile(textfile):
        print("%s not found in %s" % (textfile, os.getcwd()))
        return False
    if not os.path.isfile(circfile):
        print("%s not found in %s" % (circfile, os.getcwd()))
        return False
    
    # delete all absolute paths in circ file (recursively: also in referenced circ files):
    circfilepattern = re.compile(r'^\s*\<lib desc="file#(?P<path>.*)" name="\d+"/\>\s*$')
    abspathpattern = re.compile(r'^\s*\<lib desc="file#.*[\\/]\w*\.circ" name="\d+"/\>\s*$')
    def remove_absolute_paths_from_circ_file(filename):
        if not os.path.isfile(filename):
            os.chdir(startdir)
            raise ValueError("%s could not be found in %s" % (filename, os.getcwd()))
        f = open(filename, 'r')
        reffiles = []
        content = ""
        for line in f.readlines():
            m = circfilepattern.search(line)
            if m:
                path = m.group("path")
                reffile = path.split("\\")[-1].split("/")[-1]
                reffiles.append(reffile) # DO NOT use os.path.basename because it uses the pathseparator of your current os
                if path != reffile:
                    print("In %s: replacing \"%s\" by \"%s\"" % (filename, path, reffile))
                    line = line.replace(path, reffile)
            content += line
        f.close()
        f = open(filename, 'w')
        f.write(content)
        f.close()
        for reffile in reffiles:
            remove_absolute_paths_from_circ_file(reffile)
    startdir = os.getcwd()
    path, filename = os.path.split(circfile)
    if path: os.chdir(path)
    try:
        remove_absolute_paths_from_circ_file(filename)
    except ValueError as e:
        print(e)
        return False
    if path: os.chdir(startdir)

    testfile = os.path.splitext(textfile)[0] + ".test"
    errorfile = os.path.splitext(textfile)[0] + ".error"
    
    debugtraces = compiler(textfile, testfile, width, nr_of_tests)
    
 
    if not debugtraces:
        print("Error reading test file %s" % testfile)
        return False

    # run the tests with logisim
    print("starting tests...")
    
    result = True
    testfiles = debugtraces.keys()
    testfiles = sorted(testfiles)
    for testfile in testfiles:
        debugtrace = debugtraces[testfile]
        reportfile = os.path.splitext(testfile)[0] + os.path.splitext(testfile)[1].replace("test", "report")
        print("")
        print("testing %s --> %s" % (testfile, reportfile))
        command = "java -jar %s %s -tty table -load %s > %s" % (logisim, circfile, testfile, reportfile)
        #print command
        import subprocess
        f = open(reportfile, 'w')
        f2 = open(errorfile, 'w')
        p = subprocess.Popen(["java", "-jar", logisim, circfile, "-tty", "table", "-load", testfile], stdout=f, stderr=f2)
        p.wait()
        f.close()
        f2.close()
        # check whether logisim produced an error; stderr was redirected to f2
        f2 = open(errorfile, 'r')
        lines = f2.readlines()
        f2.close()
        if len(lines) > 0:
            print("Logisim verification failed, the following error occurred:")
            for l in lines: print(">>> %s" % l)
            os.remove(errorfile)
            result = False
            continue
        else:
            os.remove(errorfile)
        
        # parse results
        (nr_of_tests, errors, failures) = parser(reportfile, debugtrace, width, nr_of_tests)
        
        print("%d tests done, %d errors, %d failures" % (nr_of_tests, errors, failures))
    return result


if __name__ == "__main__":
    import sys, os
    if len(sys.argv) != 4:
        print("usage: python Test.py option <file_to_compile.txt> <file_to_test.circ>")
        print("         options:")
        print("             -a     :   test alu")
        print("             -s     :   test simple datapath (only r-type and sw/lw)")
        print("             -f     :   test full datapath (all instructions)")
        exit(1)
    if sys.argv[1].strip() == "-a":
        compiler = ALUtestcompiler
        parser = ALUparser
    elif sys.argv[1].strip() == "-s":
        compiler = SimpleDatapathtestcompiler
        parser = SimpleDatapathparser
    elif sys.argv[1].strip() == "-f":
        compiler = Datapathtestcompiler
        parser = Datapathparser
    try:
        textfile = sys.argv[2]
        f = open(textfile, 'r')
    except IOError:
        print("filename %s not found" % textfile)
        exit(1)
    if not os.path.isfile(sys.argv[3]):
        print("filename %s not found" % textfile)
    try:
        circfile = sys.argv[3]
        f = open(circfile, 'r')
        f.close()
    except IOError:
        print("filename %s not found" % circfile)
        exit(1)
    if not Test(textfile, circfile, compiler, parser):
        exit(1)
