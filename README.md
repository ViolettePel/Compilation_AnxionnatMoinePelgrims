# Compilation_AnxionnatMoinePelgrims
Advanced Compilation Project

Notre projet mit en commun se trouve dans compilation.py.
Actuellement, l'exemple de programme se trouvant dans ce fichier sert à démontrer que le pretty printer fonctionne et n'est pas destiné à être compilé.

Afin de compiler, entrer les commandes :

nasm -f elf64 name.asm
gcc -no-pie -fno-pie name.o
./a.out 23 45 ...

Où name.asm est le nom de fichier à renseigner ligne 531, de même pour name.o.
Les valeurs à renseigner à la suite ./a.out sont les valeurs des variables renseignées dans main.

La multiplication n'a pas été implémentée dans notre code.


Spécifiquement aux fonctions :

Les fonctions ne peuvent prendre qu'un argument. Elles ne peuvent pas retourner de valeur à l'intérieur d'une variable mais peuvent s'appeler et faire appel à printf.
Les fonctions se terminent par un return pour des problèmes de sémentique mais ne retournent rien.
Les variables utilisées sont des variables globales, attention à ne pas utiliser deux fois le même nom si vous souhaitez des variables différentes.

Spécifiquement aux pointeurs :

N'hésitez pas à regarder la grammaire pour découvrir ce qui a été implémenté dans le code.
Il est possible d'assigner un pointeur, d'aller chercher la valeur assignée à un pointeur et d'aller chercher la valeur d'un pointeur de pointeur en écrivant *(*(p)). 


Exemples de code pour les fonctions à renseigner ligne 509 :

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

Exemples de code pour les pointeurs à renseigner ligne 509 :

main(x){
    *p=2;
    *p = &x;
    x = x + 1;
    return (*p);
}


N'hésitez pas à rajouter des données à simplifier volontairement pour tester l'optimisation.