import lark

grammaire = lark.Lark(r"""
exp : SIGNED_NUMBER              -> exp_nombre
| IDENTIFIER                     -> exp_var
| exp OPBIN exp                  -> exp_opbin
| "(" exp ")"                    -> exp_par
| fct_call                       -> exp_call
com : IDENTIFIER "=" exp ";"     -> assignation
| "if" "(" exp ")" "{" bcom "}"  -> if
| "while" "(" exp ")" "{" bcom "}"  -> while
| "print" "(" exp ")" ";"              -> print
| fct_call ";"                      -> call
bcom : (com)*
fct_call : IDENTIFIER "(" var_list ")"
prg : fct "main" "(" var_list ")" "{" bcom "return" "(" exp ")" ";"  "}"        -> complex
| "main" "(" var_list ")" "{" bcom "return" "(" exp ")" ";"  "}"                -> basic
fct : IDENTIFIER "(" var_list ")" "{" bcom "return" "(" exp ")" ";"  "}"
var_list :                              -> vide
| IDENTIFIER (","  IDENTIFIER)*
| SIGNED_NUMBER (","  SIGNED_NUMBER)*
IDENTIFIER : /[a-zA-Z][a-zA-Z0-9]*/
OPBIN : /[+\-*>]/
%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
""",start="prg")

op = {'+' : 'add', '-' : 'sub'}

def asm_exp(e):
    if e.data == "exp_nombre":
        return f"mov rax, {e.children[0].value}\n"
    elif e.data == "exp_var":
        return f"mov rax, [{e.children[0].value}]\n"
    elif e.data == "exp_par":
        return asm_exp(e.children[0])
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

def pp_exp(e):
    if e.data in {"exp_nombre", "exp_var"}:
        return e.children[0].value
    elif e.data == "exp_par":
        return f"({pp_exp(e.children[0])})"
    elif e.data == "exp_call":
        return f"{e.children[0].children[0]} ({pp_var_list(e.children[0].children[1])})"
    else:
        return f"{pp_exp(e.children[0])} {e.children[1].value} {pp_exp(e.children[2])}"

def vars_exp(e):
    if e.data  == "exp_nombre":
        return set() 
    elif e.data ==  "exp_var":
        return { e.children[0].value }
    elif e.data == "exp_par":
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
    if c.data == "assignation":
        E = asm_exp(c.children[1])
        return f"""
        {E}
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

def pp_com(c):
    if c.data == "assignation":
        return f"{c.children[0].value} = {pp_exp(c.children[1])};"
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


def vars_com(c):
    if c.data == "assignation":
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
    if p.data == "basic" :
        f = open("moule_solene.asm")
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
    else :
        f = open("moule_solene.asm")
        moule = f.read()
        F = asm_fct(p.children[0])
        moule = moule.replace("DECL_FCTN", F)
        C = asm_bcom(p.children[2])
        moule = moule.replace("BODY", C)
        E = asm_exp(p.children[3])
        moule = moule.replace("RETURN", E)
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

def pp_prg(p):
    if p.data == "basic":
        L = pp_var_list(p.children[0])
        C = pp_bcom(p.children[1])
        R = pp_exp(p.children[2])
        return "main( %s ) {\n%s\nreturn(%s);\n}" % (L, C, R)
    elif p.data == "complex":
        F = pp_fct(p.children[0])
        L = pp_var_list(p.children[1])
        C = pp_bcom(p.children[2])
        R = pp_exp(p.children[3])
        return "%s \n\nmain( %s ) {\n%s\nreturn(%s);\n}" % (F, L, C, R)

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
    pop rdi
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

def pp_fct(f):
    N = f.children[0].value
    L = pp_var_list(f.children[1])
    C = pp_bcom(f.children[2])
    R = pp_exp(f.children[3])
    return "%s( %s ) {\n%s\nreturn(%s);\n}" % (N, L, C, R)


ast = grammaire.parse("""
double(j){
    j=j+j;
    print(j);
    return(j);
}

main(u){
    u=u+1;
    double(u);
    return(u);  
}
""")

print(pp_prg(ast))

asm = asm_prg(ast)
f = open("test.asm", "w")
f.write(asm)
f.close()




