import lark
from lark import Tree,Token

grammaire = lark.Lark(r"""
                      
exp : SIGNED_NUMBER                     -> exp_nombre
| IDENTIFIER                            -> exp_var
| exp OPBIN exp                         -> exp_opbin
| "(" exp ")"                           -> exp_par
| "*" exp                               -> exp_pnt_to_val
| "&" IDENTIFIER                        -> exp_pnt
| fct_call                              -> exp_call

com : IDENTIFIER "=" exp ";"            -> assignation_var
| "*" IDENTIFIER "=" exp ";"            -> assignation_val_to_pnt
| "*"IDENTIFIER"=""malloc""("exp")"";"  -> memory_allocation
| "if" "(" exp ")" "{" bcom "}"         -> if
| "while" "(" exp ")" "{" bcom "}"      -> while
| "print" "(" exp ")" ";"               -> print
| fct_call ";"                          -> call

bcom : (com)*

fct : IDENTIFIER "(" var_list ")" "{" bcom "return" "(" exp ")" ";"  "}"

fct_call : IDENTIFIER "(" var_list ")"

prg : fct "main" "(" var_list ")" "{" bcom "return" "(" exp ")" ";"  "}"        -> complex
| "main" "(" var_list ")" "{" bcom "return" "(" exp ")" ";"  "}"                -> basic

var_list :                             -> vide
| IDENTIFIER (","  IDENTIFIER)*        -> aumoinsune

IDENTIFIER : /[a-zA-Z][a-zA-Z0-9]*/
OPBIN : /[+\-*>]/

%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
""",start="prg")


#Fonctions utiles

op = {'+' : 'add', '-' : 'sub', '*' : 'mul'}

def operation(op, nb1, nb2):
    if op == "+":
        return nb1 + nb2
    elif op == "-":
        return nb1 - nb2
    elif op == "*":
        return nb1*nb2 
    
cpt = 0
def next():
    global cpt
    cpt += 1
    return cpt

def int_to_long(i):
    Hex={1:"1",2:"2",3:"3",4:"4",5:"5",6:"6",7:"7",8:"8",9:"9",0:"0",10:"a",11:"b",12:"c",13:"d",14:"e",15:"f"}
    h="";q=i;r=0
    for i in range(16):
        r=q%16
        q=q//16
        h = Hex[r] + h
    return "0x"+h


#Fonctions liées aux listes de variables

def pp_var_list(vl):
    return ", ".join([t.value for t in vl.children])


#Fonctions liées aux expressions

def pp_exp(e):
    if e.data in {"exp_nombre", "exp_var"}:
        return e.children[0].value
    
    elif e.data == "exp_par":
        return f"({pp_exp(e.children[0])})"
    
    elif e.data == "exp_pnt_to_val":
        return f"*{pp_exp(e.children[0])}"
    
    elif e.data == "exp_pnt":
        return f"&{e.children[0].value}"
    
    elif e.data == "exp_call":
        return f"{e.children[0].children[0]} ({pp_var_list(e.children[0].children[1])})"
    
    else:
        return f"{pp_exp(e.children[0])} {e.children[1].value} {pp_exp(e.children[2])}"

def asm_exp(e):
    #TODO
    if e.data == "exp_nombre":
        return f"mov rax, {e.children[0].value}\n"
    
    elif e.data == "exp_var":
        return f"mov rax, [{e.children[0].value}]\n"
    
    elif e.data == "exp_par":
        return asm_exp(e.children[0])
    
    elif e.data == "exp_pnt_to_val":
        return f"""{asm_exp(e.children[0])}
        mov rbx, [rax] \n
        mov rax, rbx \n"""
        
    elif e.data == "exp_pnt":
        return f"mov rax, {e.children[0].value}\n"
    
    elif e.data == "exp_call":
        if e.children[0].children[1].data == "vide":
            return f"call {e.children[0]}\n"
    
    else:
        E1 = asm_exp(e.children[0])
        E2 = asm_exp(e.children[2])
        return f"""
        {E2}
        push rax
        {E1}
        pop rbx
        {op[e.children[1].value]} rax, rbx
        """
        
def vars_exp(e):
    if e.data  == "exp_nombre":
        return set() 
    
    elif e.data in  {"exp_var", "exp_pnt"}:
        return { e.children[0].value }
    
    elif e.data in { "exp_par", "exp_pnt_to_val"}:
        return vars_exp(e.children[0])
    
    else:
        L = vars_exp(e.children[0])
        R = vars_exp(e.children[2])
        return L | R

def type_exp(e):
    if e.data == "exp_nombre":
        return True, int(e.children[0].value)
    
    elif e.data in {"exp_var", "exp_pnt", "exp_call"}:
        return False, None
    
    elif e.data =="exp_opbin":
        type1, value1 = type_exp(e.children[0])
        type2, value2 = type_exp(e.children[2])
        if value1 and value2:
            return True, operation(e.children[1], value1, value2)
        else:
            return False, None
        
    elif e.data in {"exp_par", "exp_pnt_to_val"}:
        return type_exp(e.children[0])

def simplify_zero_exp(e):

    if e.data in {"exp_par", "exp_pnt_to_val"}:
        temp = simplify_zero_exp(e.children[0])
        if temp.data in {"exp_opbin", "exp_par", "exp_pnt_to_val"}:
            e.children[0] == temp
        else:
            e = temp
            
    elif e.data == "exp_opbin":
        if e.children[1] == "+" or e.children[1] == "-":
            if (e.children[0].children[0] == '0') or (e.children[2].children[0] == '0'):
                if e.children[0].children[0] != '0':
                    return simplify_zero_exp(e.children[0])
                elif e.children[2].children[0] != 0:
                    return simplify_zero_exp(e.children[2])
        
        if e.children[1] == "*" or e.children[1] == "/":
            if (e.children[0].children[0] == '1') or (e.children[2].children[0] == '1'):
                if e.children[0].children[0] != '1':
                    return e.children[0]
                else: return e.children[2]
    return e

def simplify_op_exp(e):

    type, value = type_exp(e)

    if type == True:
        return Tree('exp_nombre', [Token('SIGNED_NUMBER', f'{value}')])
    
    elif e.data == "exp_opbin":
        e.children[0] = simplify_op_exp(e.children[0])
        e.children[2] = simplify_op_exp(e.children[2])
        return e
    
    elif e.data in {"exp_par", "exp_pnt_to_val"}:
        temp = simplify_op_exp(e.children[0])
        if temp.data in {"exp_opbin", "exp_par", "exp_pnt_to_val"}:
            e.children[0] == temp
        else:
            e = temp
    
    return e


#Fonctions liées aux commandes

def pp_com(c):
    if c.data == "assignation_var":
        return f"{c.children[0].value} = {pp_exp(c.children[1])};"
    
    elif c.data == "assignation_val_to_pnt":
        return f"*{c.children[0].value} = {pp_exp(c.children[1])};"
    
    elif c.data == "memory_allocation":
        return f"*{c.children[0].value} = malloc({pp_exp(c.children[1])})"
    
    elif c.data == "call":
        return f"{c.children[0].children[0]}({pp_var_list(c.children[0].children[1])});"
    
    elif c.data == "if":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"if ({pp_exp(c.children[0])}) {{{x}}}"
    
    elif c.data == "while":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"while ({pp_exp(c.children[0])}) {{{x}}}"
    
    elif c.data == "print":
        return f"print({pp_exp(c.children[0])});"

def asm_com(c):
    if c.data == "assignation_var":
        E = asm_exp(c.children[1])
        return f"""
        {E}
        mov [{c.children[0].value}], rax        
        """
        
    elif c.data == "assignation_val_to_pnt":
        if c.children[1].data == "exp_int":
            return f"mov qword [{c.children[0].value}], {int_to_long(int(c.children[1].children[0].value))}\n"
        return f"""{asm_exp(c.children[1])}
        mov [{c.children[0].value}], rax
        """
        
    elif c.data == "memory_allocation":
        return f"""{asm_exp(c.children[1])}
        mov rdi, rax
        call malloc
        mov [{c.children[0].value}], rax
        """
        
    elif c.data == "call":
        if c.children[0].children[1].data == "vide":
            return f"""
            call {c.children[0].children[0]}
            """
    
        else :
            return f"""
            mov rax, [{c.children[0].children[1].children[0]}]
            push rax
            call {c.children[0].children[0]}
            """
            
    elif c.data == "if":
        E = asm_exp(c.children[0])
        C = asm_bcom(c.children[1])
        n = next()
        return f"""
        {E}
        cmp rax, 0
        jz fin{n}
        {C}
fin{n} : nop
"""

    elif c.data == "while":
        E = asm_exp(c.children[0])
        C = asm_bcom(c.children[1])
        n = next()
        return f"""
        debut{n} : {E}
        cmp rax, 0
        jz fin{n}
        {C}
        jmp debut{n}
fin{n} : nop
"""

    elif c.data == "print":
        E = asm_exp(c.children[0])
        return f"""
        {E}
        mov rdi, fmt
        mov rsi, rax
        call printf
        """
        
def vars_com(c):
    if c.data in {"assignation_var", "assignation_val_to_pnt", "memory_allocation"}:
        R = vars_exp(c.children[1])
        return {c.children[0].value} | R
    
    elif c.data == "call":
        return set()
    
    elif c.data in {"if", "while"}:
        B = vars_bcom(c.children[1])
        E = vars_exp(c.children[0]) 
        return E | B
    
    elif c.data == "print":
        return vars_exp(c.children[0])

def simplify_com(c):
    if c.data in {"assignation_var", "assignation_val_to_pnt", "memory_allocation"}:
        c.children[1] = simplify_zero_exp(c.children[1])
        c.children[1] = simplify_op_exp(c.children[1])

    elif c.data in {"if", "while"}:
        c.children[0] = simplify_zero_exp(c.children[0])
        c.children[0] = simplify_op_exp(c.children[0])
        simplify_bcom(c.children[1])
    
    elif c.data == "print":
        c.children[0] = simplify_zero_exp(c.children[0])
        c.children[0] = simplify_op_exp(c.children[0])
        

#Fonctions liées aux blocs de commandes

def asm_bcom(bc):
    return "".join([asm_com(c) for c in bc.children])

def pp_bcom(bc):
    return "\n".join([pp_com(c) for c in bc.children])

def vars_bcom(bc):
    S = set()
    for c in bc.children:
        S = S | vars_com(c)
    return S

def simplify_bcom(bc):
    for c in bc.children:
        simplify_com(c)
        
#Fonctions liées aux fonctions

def pp_fct(f):
    N = f.children[0].value
    L = pp_var_list(f.children[1])
    C = pp_bcom(f.children[2])
    R = pp_exp(f.children[3])
    return "%s( %s ) {\n%s\nreturn(%s);\n}" % (N, L, C, R)

def asm_fct(f):
    e = f""""""
    for i in range(len(f.children[1].children)):
        e = e + f"""
        mov rax, [rbp+{ 8*(i+2)}]
        mov [{f.children[1].children[i]}], rax
        """

    return f"""{f.children[0].value} :
    push rbp
    mov rbp, rsp
    sub rsp, 8*1
    
    push rdi
    push rsi
    
    {e}

    {asm_bcom(f.children[2])}
    pop rsi
    pop rsi
    mov rsp, rbp
    pop rbp
    ret
    """

def vars_fct(f):
    L = set([t.value for t in f.children[1].children])
    C = vars_bcom(f.children[2])
    R = vars_exp(f.children[3])
    return L | C | R

def simplify_fct(f):
    simplify_bcom(f.children[2])
    f.children[3] = simplify_zero_exp(f.children[3])
    f.children[3] = simplify_op_exp(f.children[3])


#Fonctions liées au programme

def pp_prg(p):
    if p.data == "basic":
        L = pp_var_list(p.children[0])
        C = pp_bcom(p.children[1])
        R = pp_exp(p.children[2])
        return "main( %s ) {\n%s\nreturn(%s);\n}\n" % (L, C, R)
    
    elif p.data == "complex":
        F = pp_fct(p.children[0])
        L = pp_var_list(p.children[1])
        C = pp_bcom(p.children[2])
        R = pp_exp(p.children[3])
        return "%s \n\nmain( %s ) {\n%s\nreturn(%s);\n}\n" % (F, L, C, R)

def asm_prg(p):
    if p.data == "basic" :
        f = open("moule.asm")
        moule = f.read()
        F = """"""
        C = asm_bcom(p.children[1])
        moule = moule.replace("BODY", C)
        E = asm_exp(p.children[2])
        moule = moule.replace("RETURN", E)
        G = f"""
        call printf
        """
        moule = moule.replace("PRINT", G)
        D = "\n".join([f"{v} : dq 0" for v in vars_prg(p)])
        moule = moule.replace("DECL_VARS", D)
        s = ""
        for i in range(len(p.children[0].children)):
            v = p.children[0].children[i].value
            e = f"""
            mov rbx, [argv]
            mov rdi, [rbx + { 8*(i+1)}]
            xor rax, rax
            call atoi
            mov [{v}], rax
            """
            s = s + e
        moule = moule.replace("INIT_VARS", s) 
        
    else :
        f = open("moule.asm")
        moule = f.read()
        F = asm_fct(p.children[0])
        moule = moule.replace("DECL_FCTN", F)
        C = asm_bcom(p.children[2])
        moule = moule.replace("BODY", C)
        E = asm_exp(p.children[3])
        moule = moule.replace("RETURN", E)
        G = f"""
        push rcx
        call printf
        pop rcx
        pop rax
        """
        moule = moule.replace("PRINT", G)
        D = "\n".join([f"{v} : dq 0" for v in vars_prg(p)])
        moule = moule.replace("DECL_VARS", D)
        s = ""
        for i in range(len(p.children[1].children)):
            v = p.children[1].children[i].value
            e = f"""
            mov rbx, [argv]
            mov rdi, [rbx + { 8*(i+1)}]
            xor rax, rax
            call atoi
            mov [{v}], rax
            """
            s = s + e
        moule = moule.replace("INIT_VARS", s)   
    return moule

def vars_prg(p):
    if p.data == "basic" :
        L = set([t.value for t in p.children[0].children])
        C = vars_bcom(p.children[1])
        R = vars_exp(p.children[2])
        return L | C | R
    
    else :
        M = vars_fct(p.children[0])
        L = set([t.value for t in p.children[1].children])
        C = vars_bcom(p.children[2])
        R = vars_exp(p.children[3])
        return M | L | C | R

def simplify_prg(p):
    if p.data == "basic":
        simplify_bcom(p.children[1])
        p.children[2] = simplify_zero_exp(p.children[2])
        p.children[2] = simplify_op_exp(p.children[2])
        
    else:
        simplify_fct(p.children[0])
        simplify_bcom(p.children[2])
        p.children[3] = simplify_zero_exp(p.children[3])
        p.children[3] = simplify_op_exp(p.children[3])

#Programme

# Ce programme sert uniquement à montrer que tout fonctionne lors du pretty print, 
# il n'est pas destiné à être compilé.
ast = grammaire.parse("""
double(j){
    j=j+j+0;
    *p = &x;
    *p=(2+6);
    print(j);
    return(j);
}

main(u){
    u=u+1;
    *p=(2+5);
    double(u);
    return(u);
}
""")

print(pp_prg(ast))

simplify_prg(ast)
print(pp_prg(ast))

asm = asm_prg(ast)
f = open("test.asm", "w")
f.write(asm)
f.close()