import lark
from lark import Tree,Token

grammaire = lark.Lark(r"""
exp : SIGNED_NUMBER                -> exp_nombre    
| IDENTIFIER                       -> exp_var
| exp OPBIN exp                    -> exp_opbin
| "(" exp ")"                      -> exp_par
com : IDENTIFIER "=" exp ";"       -> assignation
| "if" "(" exp ")" "{" bcom "}"    -> if
| "while" "(" exp ")" "{" bcom "}" -> while
| "print" "(" exp ")"              -> print
bcom : (com)*
prog : "main" "(" var_list ")" "{" bcom "return" "(" exp ")" ";" "}"
var_list :                         -> vide
| IDENTIFIER ("," IDENTIFIER)*     -> aumoinsune
IDENTIFIER : /[a-zA-Z][a-zA-Z0-9]*/
OPBIN : /[+\-*>]/
%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
""",
start = "prog")

def pp_exp(e):
    if e.data == "exp_nombre":
        return e.children[0].value
    elif e.data == "exp_var":
        return e.children[0].value
    elif e.data == "exp_par":
        return f"({pp_exp(e.children[0])})"
    else:
        return f"{pp_exp(e.children[0])} {e.children[1].value} {pp_exp(e.children[2])}"

def vars_exp(e):
    if e.data == "exp_nombre":
        return set()
    elif e.data == "exp_var":
        return {e.children[0].value}
    elif e.data == "exp_par":
        return vars_exp(e.children[0])
    else:
        L = vars_exp(e.children[0])
        R = vars_exp(e.children[2])
        return L | R

op = {"+" : "add", "-" : "sub", "*" : "mul"}

def operation(op, nb1, nb2):
    if op == "+":
        return nb1 + nb2
    elif op == "-":
        return nb1 - nb2
    elif op == "*":
        return nb1*nb2 

def asm_exp(e):
    if e.data == "exp_nombre":
        return f"mov rax, {e.children[0].value}\n"
    elif e.data == "exp_var":
        return f"mov rax, [{e.children[0].value}]\n"
    elif e.data == "exp_par":
        return asm_exp(e.children[0])
    else:
        E2 = asm_exp(e.children[2])
        E1 = asm_exp(e.children[0])
        return f"""
    {E2}
    push rax
    {E1}
    pop rbx
    {op[e.children[1]]} rax, rbx
    """

def type_exp(e):
    if e.data == "exp_nombre":
        return True, int(e.children[0].value)
    elif e.data == "exp_var":
        return False, None
    elif e.data =="exp_opbin":
        type1, value1 = type_exp(e.children[0])
        type2, value2 = type_exp(e.children[2])
        if value1 and value2:
            return True, operation(e.children[1], value1, value2)
        else:
            return False, None
    elif e.data == "exp_par":
        return type_exp(e.children[0])
    
def simplify_zero_exp(e):

    if e.data == "exp_par":
        
        temp = simplify_zero_exp(e.children[0])
        if temp.data == "exp_opbin" or temp.data == "exp_par":
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
    elif e.data == "exp_par":

        temp = simplify_op_exp(e.children[0])
        if temp.data == "exp_opbin" or temp.data == "exp_par":
            e.children[0] == temp
        else:
            e = temp
    
    return e

cpt = 0
def next():
    global cpt
    cpt += 1
    return cpt

def pp_com(c):
    if c.data == "assignation":
        return f"{c.children[0].value} = {pp_exp(c.children[1])};"
    elif c.data == "if":
        return f"if ({pp_exp(c.children[0])}) {{\n \t{pp_bcom(c.children[1])}\n}}"
    elif c.data == "while":
        return f"while ({pp_exp(c.children[0])}) {{\n \t \t{pp_bcom(c.children[1])}\n \t}}"
    elif c.data == "print":
        return f"print({pp_exp(c.children[0])})"

def vars_com(c):
    if c.data == "assignation":
        R = vars_exp(c.children[1])
        return {c.children[0].value} | R
    elif c.data in {"if", "while"}:
        B = vars_bcom(c.children[1])
        R = vars_exp(c.children[0])
        return R | B
    elif c.data == "print":
        return vars_exp(c.children[0])
    
def asm_com(c):
    if c.data == "assignation":
        E = asm_exp(c.children[1])
        return f"""
    {E}
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

def simplify_com(c):
    if c.data == "assignation":
        
        c.children[1] = simplify_zero_exp(c.children[1])
        c.children[1] = simplify_op_exp(c.children[1])

    elif c.data == "if":
        
        c.children[0] = simplify_zero_exp(c.children[0])
        c.children[0] = simplify_op_exp(c.children[0])
        
        simplify_bcom(c.children[1])
        
    elif c.data == "while":
        
        c.children[0] = simplify_zero_exp(c.children[0])
        c.children[0] = simplify_op_exp(c.children[0])
        
        simplify_bcom(c.children[1])
        
    elif c.data == "print":
        
        c.children[0] = simplify_zero_exp(c.children[0])
        c.children[0] = simplify_op_exp(c.children[0])
    
def pp_bcom(bc):
    return "\n \t".join([pp_com(c) for c in bc.children])

def vars_bcom(bc):
    S = set()
    for c in bc.children:
        S = S | vars_com(c)
    return S

def simplify_bcom(bc):
    for c in bc.children:
        simplify_com(c)

def asm_bcom(bc):
    return "".join([asm_com(c) for c in bc.children])

def pp_var(v):
    return ", ".join([var.value for var in v.children])

def pp_prg(p):
    return f"main ({pp_var(p.children[0])}) {{\n \t{pp_bcom(p.children[1])}\n \treturn ({pp_exp(p.children[2])});\n}}"

def vars_prg(p):
    L = set([var.value for var in p.children[0].children])
    C = vars_bcom(p.children[1])
    R = vars_exp(p.children[2])
    return L | C | R

def simplify_prg(p):
    simplify_bcom(p.children[1])
    p.children[2] = simplify_zero_exp(p.children[2])
    p.children[2] = simplify_op_exp(p.children[2])
        
def asm_prg(p):
    f = open("moule_violette_pierre.asm")
    moule = f.read()
    C = asm_bcom(p.children[1])
    moule = moule.replace("BODY", C)
    R = asm_exp(p.children[2])
    moule = moule.replace("RETURN", R)
    D = "\n".join([f"{v} : dq 0" for v in vars_prg(p)])
    moule = moule.replace("DECL_VARS", D)
    I = ""
    for i in range(len(p.children[0].children)):
        v = p.children[0].children[i].value
        e = f"""
    mov rbx, [argv]
    mov rdi, [rbx+ {8*(i+1)}]
    call atoi
    mov [{v}], rax
    """
        I = I + e
    moule = moule.replace("INIT_VAR", I)
    return moule

ast = grammaire.parse("main (X,Y) { X = 0 + Y + 1 + 5 ; Y = Y * 2 * 6 * 8; X = X + X + 0; return(Y - 0);}")
#ast = grammaire.parse("main (X,Y) { while (X) {X = X - 1; Y = Y + 1 + 1;} return(Y - 0);}")
#ast = grammaire.parse("main (X,Y,Z) { if (Y - X * 1 * 2) {Z = (3 * 6) + 7;} return(Z + 3 + 6);}")
print(pp_prg(ast))

asm = asm_prg(ast)
f = open("ouf.asm","w")
f.write(asm)
f.close()

simplify_prg(ast)
print(pp_prg(ast))

asm_opt = asm_prg(ast)
f = open("ouf_opt.asm","w")
f.write(asm)
f.close()
#print(ast)

