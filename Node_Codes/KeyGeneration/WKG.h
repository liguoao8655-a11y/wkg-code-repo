#ifndef _WKG_H
#define _WKG_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif
#define M_PI 3.14159265358979323846

void LSM(int data[][2], float *a, float *b);
void mean_quantizer(double data[], int16_t result[], int KEY_SIZE);
void mean_quantizer_normal(int16_t data[], int16_t result[], int KEY_SIZE);
void dct_pre(int16_t data[], double pre_data[], int RSSI_SIZE);
void dct_pre_double(double data[], double pre_data[], int RSSI_SIZE);
void convertIntArrayToUCharArray(int16_t key[], unsigned char uc_key[], int len_msg);
void convertUCharArrayToIntArray(unsigned char uc_key[], int16_t key[], int len_msg);
int computeError(int16_t key1[], int16_t key2[], int KEY_SIZE);
void normalize(int16_t arr[], double res[], int size);

char* base64_encode(const unsigned char* input, size_t input_len);
unsigned char* base64_decode(const char *input, size_t input_len, size_t *output_len);
    
#ifdef __cplusplus
}
#endif

#endif 


