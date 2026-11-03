// Deliberate error ONLY to verify the installed sanitizer detects an error.
int main(int argc,char**){int* p=new int[1];volatile int* q=p;q[argc]=123;delete[] p;return 0;}
