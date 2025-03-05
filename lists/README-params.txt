# Refactoring Descriptor Parameters
- These are assigned into the 'args' map of descriptors
- Available arguments are listed in eclipse internal refactoring classes
- Default values for (at least) all required parameters are defined in 'default.args'

org.eclipse.ltk.core.refactoring.Refactoring
- Base class for all refactorings

The following class defines pre-defined attributes that can be used by (all?) refactorings,
but not all attributes need to be set for every refactoring type

org.eclipse.jdt.internal.corext.refactoring.JavaRefactoringDescriptorUtil
  "element"     : IJavaElement; Describes the element being refactored (element1, element2, ...)
  "input"       : IJavaElement; Describes the element being refactored
  "name"        : String      ; Name for the element being refactored
  "references"  : boolean     ; Whether or not to update references to the element as well
  "selection"   : String      ; User input selection "offset length"

org.eclipse.jdt.internal.corext.refactoring.code.InlineConstantRefactoring
  "input"     : IJavaElement(IField || ICompilationUnit) 
  "selection" : String; Format "offset length"
  "replace"   : boolean; "fReplaceAllReferences"
  "remove"    : boolean; "fRemoveDeclaration"
  
org.eclipse.jdt.internal.corext.refactoring.code.ExtractConstantRefactoring
  "input"      : IJavaElement(type = IJaveElement.COMPILATION_UNIT)
  "selection"  : String; Format "offset length"
  "replace"    : boolean; "fReplaceAllOccurrences"
  "qualify"    : boolean; "fQualifyReferencesWithDeclaringClassName"
  "visibility": integer; {package:0, private:2, protected:4, public:1}

org.eclipse.jdt.internal.corext.refactoring.code.ExtractMethodRefactoring
  "input"       : IJavaElement(type = IJavaElement.COMPILATION_UNIT)
  "selection"   : String; Format: "offset length"
  "name"        : String; Name of extracted method.
  "visibility"  : integer; {package:0, private:2, protected:4, public:1}
  "destination" : (optional; not used yet in our work)
  "comments"    : boolean; "fGenerateJavadoc"
  "replace"     : boolean; "fReplaceDuplicates"
  "exceptions"  : boolean; "fThrowRuntimeExceptions"

org.eclipse.jdt.internal.corext.refactoring.code.InlineMethodRefactoring
  "input"     : ICompilationUnit(with "selection") || IMethod(no "selection")
  "selection" : String; Format "offset length"
  "mode"      : integer; {SINGLE:0, ALL:1}
  "delete"    : boolean;

   *** See org.eclipse.jdt.internal.corext.refactoring.scripting.InlineMethodRefactoringContribution

org.eclipse.jdt.internal.corext.refactoring.code.InlineTempRefactoring
  "input"     : ICompilationUnit
  "selection" : String; Format: "offset length"

org.eclipse.jdt.internal.corext.refactoring.code.ExtractTempRefactoring
  "input"                : ICompilationUnit
  "selection"            : String; Format: "offset length"
  "name"                 : String; Name of created declaration.
  "replace"              : boolean; "fReplaceAllOccurrences"
  "replaceAllInThisFile" : boolean; "fReplaceAllOccurrencesInThisFile"
  "final"                : boolean; "fDeclareFinal"
  "varType"              : boolean; "fDeclareVarType"

org.eclipse.jdt.internal.corext.refactoring.code.IntroduceIndirectionRefactoring
  "input"      : IJavaElement(type = IJavaElement.METHOD) ; "fTargetMethod"
  "element1"   : IJavaElement(type = IJavaElement.Type)   ; "fIntermediaryType"
  "name"       : String                                   ; Intermediaty method name
  "references" : boolean                                  ; "fUpdateReferences"

The following class is ancestor to all rename processor classes 
org.eclipse.jdt.internal.corext.refactoring.rename.JavaRenameProcessor

org.eclipse.jdt.internal.corext.refactoring.rename.RenameCompilationUnitProcessor
  "input" : IJavaElement(type = IJavaElement.COMPILATION_UNIT);
  "name"  : String;

org.eclipse.jdt.internal.corext.refactoring.rename.RenameFieldProcessor
  "input"     : IJavaElement(type = IJavaElement.FIELD);
  "name"      : String;
  "references": boolean = true (jdoc says false);
  "textual"   : boolean = false; Whether textual matches should be updated (comments?)
  "getter"    : boolean = false; Whetter to rename getter
  "setter"    : boolean = false; Whether to rename setter
  "delegate"  : boolean = false; Whether to keep the original as delegate to renamed version
  "deprecate" : boolean = false; Whether to deprecate IField or IMethod

org.eclipse.jdt.internal.corext.refactoring.rename.RenameEnumConstProcessor
  "input"      : IJavaElement(type = IJavaElement.FIELD); The code says FIELD here too.
  "name"       : String;
  "references" : boolean;
  "textual"    : boolean;

org.eclipse.jdt.internal.corext.refactoring.rename.RenameLocalVariableProcessor
  "input"     : IJavaElement(type = LOCAL_VARIABLE || IJavaElement.COMPILATION_UNIT(with "selection"))
  "name"      : String;
  "selection" : String; Format: "offset length"
  "references": boolean;

org.eclipse.jdt.internal.corext.refactoring.rename.RenameMethodProcessor
  "input"     : IMethod
  "name"      : String;
  "delegate"  : boolean;
  "deprecate" : boolean;

org.eclipse.jdt.internal.corext.refactoring.rename.RenamePackageProcessor
  "input"        : IPackageFragment
  "name"         : String;
  "patterns"     : String = ""
  "references"   : boolean;
  "qualified"    : boolean;
  "textual"      : boolean;
  "hierarchical" : boolean;

org.eclipse.jdt.internal.corext.refactoring.rename.RenameTypeParameterProcessor
  "input"      : IMethod || IType
  "name"       : String;
  "parameter"  : String; Name of type parameter (used to locate the parameter by name in the method or type)
  "references" : boolean;

org.eclipse.jdt.internal.corext.refactoring.rename.RenameTypeProcessor
  "input"               : IJavaElement(type = IJavaElement.TYPE) a.k.a. IType
  "name"                : String;
  "patterns"            : String;
  "references"          : boolean;
  "textual"             : boolean;
  "qualified"           : boolean;
  "similarDeclarations" : boolean;
  "matchStrategy"       : integer in {1,2,3}; See org.eclipse.jdt.internal.corext.refactoring.rename.RenamingNameSuggestor

