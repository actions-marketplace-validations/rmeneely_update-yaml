#!/usr/bin/python3

# Modules
import sys, getopt
import re

# Syntax types
commentRegex = re.compile(r'^\s*#') # Comment
assignmentRegex = re.compile(r'^\s*\S*:\s*\S.*$')
contextRegex = re.compile(r'^\s*\S*:\s*$')
ListRegex = re.compile(r'^\s*-\s*\S*:\s*\S.*$')
ListItemConditionRegex = re.compile(r'\[\S+\]')

# Global variables
Inputfile = ''       # YAML input file
Context = ''         # The current context (e.g. 'abc.def.ghi')
ContextLst = []      # The stack of contexts (e.g. ['abc', 'def', 'ghi']
ContextIndent = {}   # The indentation for a context (e.g. Context['abc.def.ghi'] = 2)
ContextValue = {}    # The current value of the context assignment
ContextNewValue = {} # The current value of the context assignment
Condition = {}
ConditionalContext = {}
ConditionalValue = {}
ItemContext = {}
Updated = False

def enterContext(contextName, indent):
    global Context
    global ContextLst
    ContextLst.append(contextName)
    Context = '.'.join(ContextLst)
    ContextIndent[Context] = indent
    return Context

def exitContext():
    global Context
    global ContextLst
    exitedContext = Context
    if len(ContextLst) > 0:
       ContextLst.pop()
       Context = '.'.join(ContextLst)
    return exitedContext

def get_lhs(theString, delimiter):
    theList = theString.split(delimiter)
    lhs = theList[0]
    lhs = lhs.strip()
    return lhs

def get_rhs(theString, delimiter):
    theList = theString.split(delimiter)
    rhs = theString.replace(theList[0] + delimiter, '')
    rhs = rhs.strip()
    return rhs

def setValue(context, value):
    global ContextValue
    ContextValue[context] = value

def processListItem(lines, contexts):
    global Condition
    global ConditionalContext
    global ConditionalValue
    global ItemContext

    while (len(lines) > 0):
      line = lines.pop(0)
      lhs = get_lhs(line, ':')
      rhs = get_rhs(line, ':')
      _lhs = line.split(':')[0] # lhs including indent
      context = contexts.pop(0) # line context
      if context in ContextNewValue.keys():
         if context in Condition.keys():
            condition = Condition[context]
            if condition in ItemContext.keys():
               lhs = line.split(':')[0]
               line = lhs + ': ' + ContextNewValue[context]
               if rhs != ContextNewValue[context]:
                  Updated = True
      print(line)
    # Reset list item
    InList = False
    ItemContext = {}


#def writeOutputs():
#    global Updated
#    updated = 'true' if Updated else 'false'
#    print("::set-output name=updated::{}".format(updated))

def main(argv):
    # Global variables
    global Inputfile
    global Context
    global ContextLst
    global ContextIndent
    global ContextValue
    global ContextNewValue
    global Updated
    global Condition
    global ConditionalContext
    global ConditionalValue
    global ItemContext
    
    # Variables
    Inputfile = 'values.yaml'
    Updated = False
    inList = False
    itemLines = []		# List item input lines
    itemLineContexts = []  	# List item input lines context
    ItemContext = {}
    listItemContextCondition = {}
    conditionalMatch = False
    
    # Command line options
    try:
       opts, args = getopt.getopt(argv, "i:v:V:", ["infile=","var=","vars="])
    except getopt.GetoptError:
       print('update-yaml.py -i <inputfile> [-v <var=value>]')
       sys.exit(2)
    for opt, arg in opts:
        if opt in ('-v', "--var"): 
           lhs = get_lhs(arg,'=')
           rhs = get_rhs(arg,'=')
           ContextNewValue[lhs] = rhs
        elif opt in ('-V', "--vars"):
           varsLst = arg.split(',')
           for varString in varsLst:
               lhs = get_lhs(varString,'=')
               rhs = get_rhs(varString,'=')
               conditionalMatch = ListItemConditionRegex.search(varString)
               if conditionalMatch: # Assignement is dependent on context condition
                  lhs = get_lhs(varString,'[')
                  rhs = get_rhs(varString,']')
                  _lhs = get_lhs(rhs,'=')
                  lhs = lhs + _lhs
                  rhs = get_rhs(rhs,'=')
                  _list = lhs.split(']')
                  conditionVariable = get_lhs(varString,'=')
                  conditionVariable = conditionVariable.replace('[','.')
                  conditionValue = get_lhs(varString,']')
                  conditionValue = get_rhs(conditionValue,'=')
                  condition = conditionVariable + '=' + conditionValue
                  Condition[lhs] = conditionVariable + '=' + conditionValue
                  listItemContextCondition[lhs] = True
                  ConditionalValue[conditionVariable] = rhs
               ContextNewValue[lhs] = rhs
        elif opt in ("-i", "--ifile"):
           Inputfile = arg
    
    # Read yaml file
    infile = open(Inputfile, "r")
    contents = infile.read()
    infile.close
    yaml = contents.split('\n') # Create a list of the file contents
    yaml.pop() # Remove extra line created by split
    
    listIndent = 0
    for line in yaml:
        indent = len(line) - len(line.lstrip())
        comment = commentRegex.search(line)
        assignment = assignmentRegex.search(line)
        newContext = contextRegex.search(line)
        list = ListRegex.search(line)
    
        # Exit contexts
        if not comment:
           if inList:
             while (len(ContextLst) > 0) and (indent < ContextIndent[Context]):
               exitContext()
               if len(itemLines) > 0: # Process any prior item lines
                  processListItem(itemLines, itemLineContexts)
           else:
             while (len(ContextLst) > 0) and (indent <= ContextIndent[Context]):
               exitContext()
    
        # Process this line
        if comment:
           print(line)
        elif list:
           if len(itemLines) > 0: # Process any prior item lines
              processListItem(itemLines, itemLineContexts)
           itemLines.append(line)
           inList = True
           _line = line.replace('-',' ')
           listIndent = len(_line) - len(_line.lstrip()) # List indent w/o '-'
           theItem = line.replace('-', '', 1)
           lhs = get_lhs(theItem, ':')
           rhs = get_rhs(theItem, ':')
           contextName = lhs
           Context = enterContext(contextName, indent)
           itemLineContexts.append(Context)
           ItemContext[Context + '=' + rhs] = True
           setValue(Context, rhs)
           if Context in ContextNewValue.keys():
              tmpLine = line.split(':')
              if rhs != ContextNewValue[Context]:
                 Updated = True
        elif inList:
           lhs = get_lhs(line, ':')
           rhs = get_rhs(line, ':')
           itemLines.append(line) # Add to the list of item lines
           exitContext()
           Context = enterContext(lhs, indent)
           itemLineContexts.append(Context)
           ItemContext[Context + '=' + rhs] = True
        elif assignment:
           if len(itemLines) > 0: # Process any prior item lines
              processListItem(itemLines, itemLineContexts)
           lhs = get_lhs(assignment.group(), ':')
           rhs = get_rhs(assignment.group(), ':')
           Context = enterContext(lhs, indent)
           setValue(Context, rhs)
           if Context in ContextNewValue.keys():
              tmpLine = line.split(':')
              print("{}: {}".format(tmpLine[0], ContextNewValue[Context]))
              if rhs != ContextNewValue[Context]:
                 Updated = True
           else:
              print(line)
        elif newContext:
           if len(itemLines) > 0: # Process any prior item lines
              processListItem(itemLines, itemLineContexts)
           lhs = get_lhs(newContext.group(), ':')
           Context = enterContext(lhs, indent)
           print(line)
        else:
           if len(itemLines) > 0: # Process any prior item lines
              processListItem(itemLines, itemLineContexts)
           print(line)
    
    # Write the output values
    # Print any remaining list lines
    if len(itemLines) > 0:
       processListItem(itemLines, itemLineContexts)

if __name__ == "__main__":
   main(sys.argv[1:])
