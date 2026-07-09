#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "WKG.h"

void LSM(int data[][2], float *a, float *b){
	int n = 9;

    // 计算x和y的平均数
    float x_avg = 0, y_avg = 0;
    for (int i = 0; i < n; i++) {
        x_avg += data[i][0];
        y_avg += data[i][1];
    }
    x_avg /= n;
    y_avg /= n;
    printf("%f %f\n", x_avg, y_avg);

    // 计算x和y的偏差
    float x_bias[10], y_bias[10];
    for (int i = 0; i < n; i++) {
        x_bias[i] = data[i][0] - x_avg;
        y_bias[i] = data[i][1] - y_avg;
    }

    // 计算偏差乘积总和和x偏差平方总和
    float bias_product_sum = 0, x_bias_sqr_sum = 0;
    for (int i = 0; i < n; i++) {
        bias_product_sum += x_bias[i] * y_bias[i];
        x_bias_sqr_sum += x_bias[i] * x_bias[i];
    }

    // 计算斜率b和截距a
    *b = bias_product_sum / x_bias_sqr_sum;
    *a = y_avg - *b * x_avg;  
}

void mean_quantizer(double data[], int16_t result[], int KEY_SIZE) {
    double sum = 0.0;
    int split = 1;
    for (int i=split; i < (KEY_SIZE + 1); i++) {
        sum += data[i];
    }
    double mean_value = sum / KEY_SIZE;

    int index = split;
    int res_index = 0;
    while (index < (KEY_SIZE + split)) {  // ERROR!!! while (index < (KEY_SIZE + index)) !!!
        if (data[index] >= mean_value) {
            result[res_index] = 1;
        }
        else if (data[index] < mean_value) {
            result[res_index] = 0;
        }
        index++;
        res_index++;
    }
}

void mean_quantizer_normal(int16_t data[], int16_t result[], int KEY_SIZE) {
    double sum = 0.0;
    for (int i=0; i < KEY_SIZE; i++) {
        sum += data[i];
    }
    double mean_value = sum / KEY_SIZE;

    for(int i = 0; i< KEY_SIZE;i++){
        if(data[i]>=mean_value){
            result[i] = 1;
        }else{
            result[i] = 0;
        }
    }
}

// data[RSSI_SIZE], pre_data[RSSI_SIZE-1], RSSI_SIZE-1
void dct_pre(int16_t data[], double pre_data[], int RSSI_SIZE)
{
    // Compute DCT of the input data
    for (int k = 0; k < RSSI_SIZE; k++) {
        double sum = 0;
        double coeff = (k == 0) ? sqrt(1.0 / RSSI_SIZE) : sqrt(2.0 / RSSI_SIZE);
        for (int n = 0; n < RSSI_SIZE; n++) {
            sum += coeff * data[n] * cos((M_PI / RSSI_SIZE) * (n + 0.5) * k);
        }
        pre_data[k] = sum;
    }
}

void dct_pre_double(double data[], double pre_data[], int RSSI_SIZE)
{
    // Compute DCT of the input data
    for (int k = 0; k < RSSI_SIZE; k++) {
        double sum = 0;
        double coeff = (k == 0) ? sqrt(1.0 / RSSI_SIZE) : sqrt(2.0 / RSSI_SIZE);
        for (int n = 0; n < RSSI_SIZE; n++) {
            sum += coeff * data[n] * cos((M_PI / RSSI_SIZE) * (n + 0.5) * k);
        }
        pre_data[k] = sum;
    }
}

// len_msg * 8 int(key) -> len_msg unsigned char(uc_key)
void convertIntArrayToUCharArray(int16_t key[], unsigned char uc_key[], int len_msg) {
    int i, j;
    unsigned char value;
    // 将传入的key 补零
    // int key_temp[128];
    // for (i = 0; i < 128; i++) {
    //     key_temp[i] = 0;
    // }
    // for (i = 0; i < key_len; i++) {
    //     key_temp[i] = key[i];
    // }
    for (i = 0; i < len_msg; i++) {
        value = 0;
        for (j = 0; j < 8; j++) {
            value = value | (key[i * 8 + j] << (7 - j));
        }
        uc_key[i] = value;
    }
}

// len_msg unsigned char(key_uc) -> len_msg * 8 int(key)
void convertUCharArrayToIntArray(unsigned char uc_key[], int16_t key[], int len_msg) {
    int i, j;
    unsigned char value;

    for (i = 0; i < len_msg; i++) {  // i < 16
        value = uc_key[i];
        for (j = 0; j < 8; j++) {
            key[i * 8 + j] = (value >> (7 - j)) & 0x01;
        }
    }
}

// 计算两个密钥的错误数
int computeError(int16_t key1[], int16_t key2[], int KEY_SIZE) {
    int i;
    int count = 0;
    for (i = 0; i < KEY_SIZE; i++) {
        if (key1[i] != key2[i]) {
            count++;
        }
    }
    return count;
}

// Base64 编码表
static const char *base64_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

// Base64 编码
char* base64_encode(const unsigned char* input, size_t input_len) {
    char *output = (char *)malloc(((input_len + 2) / 3) * 4 + 1);
    if (output == NULL) {
        return NULL;
    }

    for (size_t i = 0, j = 0; i < input_len;) {
        uint32_t octet_a = i < input_len ? input[i++] : 0;
        uint32_t octet_b = i < input_len ? input[i++] : 0;
        uint32_t octet_c = i < input_len ? input[i++] : 0;

        uint32_t triple = (octet_a << 0x10) + (octet_b << 0x08) + octet_c;

        output[j++] = base64_chars[(triple >> 3 * 6) & 0x3F];
        output[j++] = base64_chars[(triple >> 2 * 6) & 0x3F];
        output[j++] = base64_chars[(triple >> 1 * 6) & 0x3F];
        output[j++] = base64_chars[(triple >> 0 * 6) & 0x3F];
    }

    // 处理最后一组不足 3 字节的数据
    if (input_len % 3 > 0) {
        output[((input_len + 2) / 3) * 4 - (3 - input_len % 3)] = '=';
    }
    if (input_len % 3 == 1) {
        output[((input_len + 2) / 3) * 4 - 2] = '=';
    }

    output[((input_len + 2) / 3) * 4] = '\0';

    return output;
}

// Base64 解码
unsigned char* base64_decode(const char *input, size_t input_len, size_t *output_len) {
    if (input_len % 4 != 0) {
        return NULL;
    }

    int padding = 0;
    if (input[input_len - 1] == '=') {
        padding++;
    }
    if (input[input_len - 2] == '=') {
        padding++;
    }

    *output_len = input_len / 4 * 3 - padding;
    unsigned char *output = (unsigned char *)malloc(*output_len);
    if (output == NULL) {
        return NULL;
    }

    for (size_t i = 0, j = 0; i < input_len;) {
        uint32_t sextet_a = input[i] == '=' ? 0 : strchr(base64_chars, input[i]) - base64_chars;
        uint32_t sextet_b = input[i+1] == '=' ? 0 : strchr(base64_chars, input[i+1]) - base64_chars;
        uint32_t sextet_c = input[i+2] == '=' ? 0 : strchr(base64_chars, input[i+2]) - base64_chars;
        uint32_t sextet_d = input[i+3] == '=' ? 0 : strchr(base64_chars, input[i+3]) - base64_chars;

        uint32_t triple = (sextet_a << 3 * 6)
                        + (sextet_b << 2 * 6)
                        + (sextet_c << 1 * 6)
                        + (sextet_d << 0 * 6);

        if (j < *output_len) {
            output[j++] = (triple >> 2 * 8) & 0xFF;
        }
        if (j < *output_len) {
            output[j++] = (triple >> 1 * 8) & 0xFF;
        }
        if (j < *output_len) {
            output[j++] = (triple >> 0 * 8) & 0xFF;
        }

        i += 4;
    }

    return output;
}


// 归一化
void normalize(int16_t arr[], double res[], int size) {
    int16_t min = arr[0];
    int16_t max = arr[0];
    // 找出数组中的最小值和最大值
    for (int i = 1; i < size; i++) {
        if (arr[i] < min) {
            min = arr[i];
        }
        if (arr[i] > max) {
            max = arr[i];
        }
    }
    
    // 归一化处理
    for (int i = 0; i < size; i++) {
        res[i] = (arr[i] - min) / (float)(max - min);
    }
}