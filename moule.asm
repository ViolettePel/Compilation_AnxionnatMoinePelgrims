extern printf, atoi, malloc

section .data
fmt : db "%d", 10, 0
argc : dq 0
argv : dq 0
DECL_VARS

section .text
global main

DECL_FCTN

main : 
    push rbp
    mov [argc], rdi
    mov [argv], rsi
    INIT_VARS
    BODY
    RETURN
    mov rdi, fmt
    mov rsi, rax
    PRINT
    pop rbp
    ret