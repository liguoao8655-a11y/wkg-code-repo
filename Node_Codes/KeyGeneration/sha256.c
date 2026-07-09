#include<stdio.h>
#include "sha256.h"

#define H0  0x6a09e667
#define H1  0xbb67ae85
#define H2  0x3c6ef372
#define H3  0xa54ff53a
#define H4  0x510e527f
#define H5  0x9b05688c
#define H6  0x1f83d9ab
#define H7  0x5be0cd19
u32 Wt[64];
u32 Kt[64] = { 0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
				0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
				0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
				0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
				0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
				0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
				0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
				0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
				0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
				0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
				0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
				0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
				0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
				0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
				0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
				0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2 };
u32 Ch(u32 x, u32 y, u32 z)
{
	return (x & y) ^ (~x & z);
}
u32 cycle_rshift(u32 x,u32 n)
{
	return 	((x & (((u32)1 << n) - 1)) << (32 - n))|(x >> n);
}
u32 Sum0(u32 x)
{
	return cycle_rshift(x, 2) ^ cycle_rshift(x, 13) ^ cycle_rshift(x, 22);
}
u32 Sum1(u32 x)
{
	return cycle_rshift(x, 6) ^ cycle_rshift(x, 11) ^ cycle_rshift(x, 25);
}
u32 Sigma0(u32 x)
{
	return cycle_rshift(x, 7) ^ cycle_rshift(x, 18) ^ (x>>3);
}
u32 Sigma1(u32 x)
{
	return cycle_rshift(x, 17) ^ cycle_rshift(x, 19) ^ (x >> 10);
}
u32 Ma(u32 x, u32 y, u32 z)
{
	return (x & y) ^ (x & z)^ (y & z);
}

void sha_init(struct sha256 *s)
{
	s->hash[0] = H0;
	s->hash[1] = H1;
	s->hash[2] = H2;
	s->hash[3] = H3;
	s->hash[4] = H4;
	s->hash[5] = H5;
	s->hash[6] = H6;
	s->hash[7] = H7;
	s->hash_length = 0;
	s->index  = 0;
	s->offset = 0;
}
void sha_caculator(struct sha256* s)//先补齐 Wt,然后循环64次加密
{
	u8 i = 0;
	u32 m0, s0, s1,c1,t1;

	u32 temp[8];
	for(i=0;i<8;i++)
		temp[i]=s->hash[i];

	for (i = 0; i < 16; i++)
		Wt[i] = s->block[i];

	for (i = 16; i < 64; i++)
		Wt[i] = Sigma1(Wt[i-2])+ Wt[i-7]+Sigma0(Wt[i - 15])+ Wt[i - 16];
	
	for (i = 0; i < 64; i++)
	{
		s0 = Sum0(temp[0]);

		s1 = Sum1(temp[4]);

		m0 = Ma(temp[0], temp[1], temp[2]);

		c1 = Ch(temp[4], temp[5], temp[6]);

		t1 = s1+c1+temp[7]+Wt[i] + Kt[i];

		temp[7] = temp[6];
		temp[6] = temp[5];
		temp[5] = temp[4];
		temp[4] = temp[3]+ t1;
		temp[3] = temp[2];
		temp[2] = temp[1];
		temp[1] = temp[0];
		temp[0] = t1+m0+s0;
	
	}

	for (i = 0; i < 8; i++)
		s->hash[i]+=temp[i];
}
void sha_updata(struct sha256* s,const char *str,u64 len)
{
	u64 i = 0;
	u64 count;
	s->hash_length += len;
	if (s->offset!=0)//说明没有4字节对齐
	{
		if (s->offset + len < 4)
		{
			for (i = s->offset; i < s->offset+len; i++)
			{
				s->block[s->index]  |= (((u32)(*str)) << (8 * (3 - i)));
				str++;
			}
			s->offset += len;
			return;
		}
		else
		{
			len = len + s->offset - 4;
			for (i = s->offset; i < 4; i++)
			{
				s->block[s->index]  |= (((u32)(*str)) << (8 * (3 - i)));
				str++;
			}
			s->index++;
			if (s->index == 16)
			{
				sha_caculator(s);//满足512bit 16Word加密一次
				s->index = 0;
			}
		}
	}
	count = (len >> 2);//计算这次加密有多少个Word
	s->offset = len % 4;//对齐Word剩余的byte


	for(i=0;i<count;i++)
	{

		s->block[s->index] = (((u32)(*str))		<< 24) |
								((*(str	+	1))		<< 16) |
								((*(str + 2))	<< 8) |
								(*(str + 3));
		s->index++;

		str += 4;

		if (s->index == 16)
		{
			sha_caculator(s);//满足512bit 16Word加密一次
			s->index = 0;
		}
	}


	s->block[s->index] = 0;//对齐Word剩余的byte写在 s->index 位置上，供下一次update使用

	for (i = 0; i < s->offset; i++)
	{
		s->block[s->index] |= (((u32)(*str)) << (8 * (3 - i)));
		str++;
	}
	
}
void sha_final(struct sha256* s)
{
	u8 temp=s->hash_length % 64;//计算需要填充多少byte
	u8 fill[4] = { 0x80,0x0,0x0,0x0 };
	u32 i;
	if (temp == 56)//则需要填充一个512bit
	{
		//补齐前一次的512bit
		if (s->offset != 0)
		{
			for (i = 0; i < 4-s->offset; i++)
			s->block[s->index]  |= (fill[i]<< (8 * (3 - i-s->offset)));

			s->index++;
		}
		else
		{
			s->block[s->index] = 0x80000000;
			s->index++;
		}
		for (i = s->index; i < 16; i++)
			s->block[i] = 0;

		sha_caculator(s);

	
		for(i=0;i<14;i++)
		s->block[i] = 0;

		s->block[14] = s->hash_length >> 29;
		s->block[15] = s->hash_length << 3 & 0xffffffff;
		sha_caculator(s);

	}
	else
	{
		if (s->offset != 0)
		{
			for (i = 0; i < 4-s->offset; i++)
				s->block[s->index]  |= (fill[i] << (8 * ( 3 - i - s->offset)));

			s->index++;
		}
		else
		{
			s->block[s->index] = 0x80000000;
			s->index++;
		}
		for (i = s->index; i < 14; i++)
			s->block[i] = 0;
		s->block[14] = s->hash_length>> 29;
		s->block[15] = s->hash_length<<3 & 0xffffffff;
		sha_caculator(s);
	}
}
