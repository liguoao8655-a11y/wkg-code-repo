#ifndef _SHA256_H
#define _SHA256_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned int u32;
typedef unsigned char u8;
typedef unsigned long long u64;

struct sha256
{
	u32 block[16];	//加密的measage
	u32 hash[8];	//hash的结果
	u64 hash_length;//总共hash的byte数
	u8  offset;		//一个update未对齐Word(4字节)的字节数
	u8  index;		//当前已经写到block的位置
};

void sha_init(struct sha256 *s);
void sha_caculator(struct sha256* s);
void sha_updata(struct sha256* s,const char *str,u64 len);
void sha_final(struct sha256* s);
    
#ifdef __cplusplus
}
#endif

#endif 


