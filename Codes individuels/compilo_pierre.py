import lark

#peut-être faire d  e &var une comm
#Dans les différentes fonctions vars, pau-être faire en sorte que les pointeurs soient initialisés différemment

grammaire = lark.Lark(r"""
exp : SIGNED_NUMBER                    -> exp_int
| IDENTIFIER                           -> exp_var
| exp OPBIN exp                        -> exp_opbin
| "(" exp ")"                          -> exp_par
| "*" exp                               -> exp_pnt_to_val
| "&" IDENTIFIER                        -> exp_pnt
com : IDENTIFIER "=" exp ";"           -> assignation_var
| "*" IDENTIFIER "=" exp ";"            -> assignation_val_to_pnt
| "*"IDENTIFIER"=""malloc""("exp")"";"  -> memory_allocation
| "if" "(" exp ")" "{" bcom "}"        -> if
| "while" "(" exp ")" "{" bcom "}"     -> while
| "print" "(" exp ")"                  -> print
bcom : (com)*
prg : "main" "(" var_list ")" "{" bcom "return" "(" exp ")" ";"  "}"
var_list :                             -> vide
| IDENTIFIER (","  IDENTIFIER)*        -> aumoinsune
IDENTIFIER : /[a-zA-Z][a-zA-Z0-9]*/
OPBIN : /[+\-*>]/
%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
""",start="prg")

op = {'+' : 'add', '-' : 'sub'}

def asm_exp(e):
    #TODO
    if e.data == "exp_int":
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

def pp_exp(e):
    if e.data in {"exp_int", "exp_var"}:
        return e.children[0].value
    elif e.data == "exp_par":
        return f"({pp_exp(e.children[0])})"
    elif e.data == "exp_pnt_to_val":
        return f"*{pp_exp(e.children[0])}"
    elif e.data == "exp_pnt":
        return f"&{e.children[0].value}"
    else:
        return f"{pp_exp(e.children[0])} {e.children[1].value} {pp_exp(e.children[2])}"

def vars_exp(e):
    #TODO
    if e.data  == "exp_int":
        return set()
    elif e.data in  {"exp_var", "exp_pnt"}:
        return { e.children[0].value }
    elif e.data in { "exp_par", "exp_pnt_to_val"}:
        return vars_exp(e.children[0])
    else:
        L = vars_exp(e.children[0])
        R = vars_exp(e.children[2])
        return L | R

cpt = 0
def next():
    global cpt
    cpt += 1
    return cpt

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

def pp_com(c):
    if c.data == "assignation_var":
        return f"{c.children[0].value} = {pp_exp(c.children[1])};"
    elif c.data == "assignation_val_to_pnt":
        return f"*{c.children[0].value} = {pp_exp(c.children[1])};"
    elif c.data == "memory_allocation":
        return f"*{c.children[0].value} = malloc({pp_exp(c.children[1])})"
    elif c.data == "if":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"if ({pp_exp(c.children[0])}) {{{x}}}"
    elif c.data == "while":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"while ({pp_exp(c.children[0])}) {{{x}}}"
    elif c.data == "print":
        return f"print({pp_exp(c.children[0])})"


#TODO pb ici
def vars_com(c):
    if c.data in {"assignation_var", "assignation_val_to_pnt", "memory_allocation"}:
        R = vars_exp(c.children[1])
        return {c.children[0].value} | R
    elif c.data in {"if", "while"}:
        B = vars_bcom(c.children[1])
        E = vars_exp(c.children[0]) 
        return E | B
    elif c.data == "print":
        return vars_exp(c.children[0])

def asm_bcom(bc):
    return "".join([asm_com(c) for c in bc.children])

def pp_bcom(bc):
    return "\n".join([pp_com(c) for c in bc.children])

def vars_bcom(bc):
    S = set()
    for c in bc.children:
        S = S | vars_com(c)
    return S

def pp_var_list(vl):
    return ", ".join([t.value for t in vl.children])

def asm_prg(p):
    f = open("moule_violette_pierre.asm")
    moule = f.read()
    C = asm_bcom(p.children[1])
    moule = moule.replace("BODY", C)
    E = asm_exp(p.children[2])
    moule = moule.replace("RETURN", E)
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
    return moule

def vars_prg(p):
    L = set([t.value for t in p.children[0].children])
    C = vars_bcom(p.children[1])
    R = vars_exp(p.children[2])
    return L | C | R

def pp_prg(p):
    L = pp_var_list(p.children[0])
    C = pp_bcom(p.children[1])
    R = pp_exp(p.children[2])
    return "main( %s ) { %s \nreturn(%s);\n}" % (L, C, R)

#TODO faire qua ça marche lol (return cassé)
ast = grammaire.parse("""main(x){
        *p = &x;
        *p=2;
        print(p)
        x=1;
        print(x)
    return (*p);
}
""")

'''Used to convert an int into a string of the quadword representation of that int'''
def int_to_long(i):
    Hex={1:"1",2:"2",3:"3",4:"4",5:"5",6:"6",7:"7",8:"8",9:"9",0:"0",10:"a",11:"b",12:"c",13:"d",14:"e",15:"f"}
    h="";q=i;r=0
    for i in range(16):
        r=q%16
        q=q//16
        h = Hex[r] + h
    return "0x"+h

print(pp_prg(ast))
asm = asm_prg(ast)
f = open("ouf.asm", "w")
f.write(asm)
f.close()