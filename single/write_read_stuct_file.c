#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// a struct to read and write
struct person
{
    uint32_t  id;
    uint32_t  salary;
};
 
int main ()
{
    FILE *outfile;
     
    // open file for writing
    outfile = fopen ("dump.dat", "w");
    if (outfile == NULL)
    {
        fprintf(stderr, "\nError opened file\n");
        exit (1);
    }
 
    struct person input1 = {1, 324};
    struct person input2 = {2, 456};
     
    // write struct to file
    fwrite (&input1, sizeof(struct person), 1, outfile);
    fwrite (&input2, sizeof(struct person), 1, outfile);
     
    if(fwrite != 0)
        printf("contents to file written successfully !\n");
    else
        printf("error writing file !\n");
 
    // close file
    fclose (outfile);

    FILE *infile;
    struct person input;
     
    // Open person.dat for reading
    infile = fopen ("dump.dat", "r");
    if (infile == NULL)
    {
        fprintf(stderr, "\nError opening file\n");
        exit (1);
    }
     
    // read file contents till end of file
    while(fread(&input, sizeof(struct person), 1, infile))
        printf ("id = %d salary = %d \n", input.id,
        input.salary);
 
    // close file
    fclose (infile);
 
    return 0;
}