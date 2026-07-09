import matplotlib.pyplot as plt
import numpy as np
import galois
# from Crypto.Util import number
import math
from galois import BCH, GF, GF2
import random
import matplotlib.pyplot as plt
import math
from statistics import mean, stdev
from scipy.fftpack import dct
import pywt
from scipy.fft import fft
from scipy.linalg import hadamard
from secrets import randbelow
import hashlib
import scipy.special
from collections import Counter
import qrcode
# import bch


#密钥熵计算
def calculate_entropy(bits_sequence):
    freq_0 = sum(1 for b in bits_sequence if b == 0) / len(bits_sequence)
    freq_1 = 1 - freq_0
    return -math.log2(max(freq_0, freq_1))

####################################################################################纠错
def galois_bch_correction(alice_bits, bob_bits):
    try:
        # 参数配置（BCH(63,30,6)）
        GF = galois.GF(2)
        bch = galois.BCH(255, 123, c=17, field=GF)

        # 数据分块编码（自动填充）
        def encode(bits):

            # padded = np.pad(bits, (0, (-len(bits)) % 30))
            # return bch.encode(padded.reshape(-1, 30)).flatten()

            pad_len = (bch.k - (len(bits) % bch.k)) % bch.k
            padded = np.pad(bits, (0, pad_len))
            return bch.encode(padded.reshape(-1, bch.k)).flatten()

            # Alice编码
        encoded = encode(alice_bits)


        bob_data=bob_bits.copy().astype(int)
        received = np.concatenate([bob_data, encoded[len(bob_bits):]])
        # 解码纠错
        # decoded = bch.decode(received.reshape(-1, 63))
        decoded = bch.decode(received.reshape(-1, bch.n))
        return decoded.flatten()[:len(alice_bits)]
    except Exception as e:
        print(f"BCH纠错失败: {str(e)}")
        return bob_bits  # 降级返回原始数据

#转化为字符串
def quantized_to_byte(quantized_data):
    binary_str = ''.join(['{:02b}'.format(q) for q in quantized_data])
    # 填充到字节的长度
    padded_binary = binary_str.ljust(len(binary_str) + (8 - len(binary_str) % 8) % 8, '0')
    # 将二进制数据转为字节数组
    byte_data = bytearray(int(padded_binary[i:i + 8], 2) for i in range(0, len(padded_binary), 8))
    return byte_data


#==============================================平衡熵==========================
def modify_consecutive_enhanced(data_list, max_run_length):
    # 转换为普通numpy数组处理
    modified = data_list.view(np.ndarray).copy()
    n = len(modified)
    i = 0
    while i < n:
        run_start = i
        current_value = modified[i]
        # 检测连续相同值段（01）
        while i < n and modified[i] == current_value:
            i += 1
        run_length = i - run_start
        # 对任何超过长度的连续段进行处理
        if run_length > max_run_length:
            num_to_flip = run_length - max_run_length
            flip_indices = random.sample(
                range(run_start, i),
                num_to_flip
            )
            modified[flip_indices] = 1 - modified[flip_indices]

    # 转换回GF(2)数组
    return galois.GF2(modified)


class SyncRandom:
    def __init__(self, seed=8):
        self.base_seed = seed
        self.counter = 0

    def generate(self, n, k):
        """确定性随机数生成（保持同步）"""
        rng = np.random.RandomState(self.base_seed + self.counter)
        indices = rng.choice(n, k, replace=False)
        self.counter += 1
        return sorted(indices.tolist())


def modify_consecutive_sync(data_list, max_run_length, sync_random):
    modified = data_list.copy()
    n = len(modified)
    one = GF2(1)
    zero = GF2(0)

    i = 0
    while i < n:
        run_start = i
        current_value = modified[i]

        # 扫描连续段
        while i < n and modified[i] == current_value:
            i += 1
        run_length = i - run_start

        if run_length > max_run_length:
            # 获取需要翻转的位置
            flip_indices = sync_random.generate(run_length, run_length - max_run_length)
            # 执行位翻转（在GF2域内）
            for idx in flip_indices:
                pos = run_start + idx
                modified[pos] = one if modified[pos] == zero else zero

    return modified



def bits_to_bytes(bits):
    bit_str = ''.join(map(str, bits.astype(int)))
    # 填充至8的倍数
    padding = (8 - len(bit_str) % 8) % 8
    bit_str += '0' * padding
    return bytearray(int(bit_str[i:i+8], 2) for i in range(0, len(bit_str), 8))


########################################################################################################量化部分
#####均值量化
# def mean_quantizer(data, a, result):
#     # 计算平均值和标准差
#     data = wavelet_pre(data)
#     plt.figure(figsize=(10, 6))
#     plt.plot(list(data), label='Quantized Alice RSSI (Binary)', color='green', marker='o')
#
#     plt.grid(True)
#     plt.legend()
#     plt.show()
#
#     mean_value = mean(data)
#     std_dev = stdev(data)
#     print(f"mean={mean_value}")
#     print(f"std={std_dev}")
#     # 阈值
#     threshold1 = mean_value + a * std_dev
#     threshold2 = mean_value - a * std_dev
#     # 数据量化
#     num = 0
#     while num < len(data):
#         if data[num] >= threshold1:
#             result[num] = 0
#         # elif data[num] < threshold2:
#         #     result[num] = 0
#         else :
#             result[num] = 1
#         num = num + 1
#     while len(result) < 128:
#         result.append(0)
#     while len(result) > 128:
#         result.pop()
#
#     return result, threshold1, threshold2
#
#
# import matplotlib.pyplot as plt
# from statistics import mean, stdev


def mean_quantizer(data, a):
    # 小波预处理
    processed_data = dct_pre(data)  # 已定义 wavelet_pre 函数
    plt.figure(figsize=(10, 6))
    plt.plot(processed_data, label='Processed RSSI', color='green', marker='o')
    plt.grid(True)
    plt.legend()
    plt.show()
    # 均值与标准差
    mean_value = mean(processed_data)
    std_dev = stdev(processed_data)
    print(f"mean = {mean_value}")
    print(f"std = {std_dev}")

    # 双阈值
    threshold1 = mean_value + a * std_dev
    threshold2 = mean_value - a * std_dev

    # 初始化结果列表
    result = []

    # 数据量化（动态追加代替索引赋值）
    for value in processed_data:
        if value >= threshold1:
            result.append(0)
        elif value < threshold2:
            result.append(1)
        else:
            result.append(1)
    # 调整结果长度为128
    if len(result) < 128:
        result += [0] * (128 - len(result))
    else:
        result = result[:128]

    return result, threshold1, threshold2
# 量化Alice和Bob的RSSI数据
def quantize_rssi(rssi_data, a=0.00):
    result = [0] * len(rssi_data)  # 初始化结果列表
    return mean_quantizer(rssi_data, a)
def quantized_to_binary(quantized_data):
    return ''.join(['{:01b}'.format(q) for q in quantized_data])

##########################################################################差分量化
def dct_pre(data):
    # dct预处理
    pre = dct(data, 2)
    split = 1
    pre_np = pre[split:]
    pre_list = pre_np.tolist()
    return pre_list

def wavelet_pre(data):
    coeffs = pywt.wavedec(data, 'db4', level=3)  # 3层分解，使用db4小波
    coeffs[0] = np.zeros_like(coeffs[0])  # 清零近似系数
    # 重构信号
    reconstructed = pywt.waverec(coeffs, 'db4')
    # 转为list并返回
    pre_list = reconstructed.tolist()
    return pre_list

def fft_pre(data):
    # FFT预处理（舍弃低频分量）
    fft_coeffs = fft(data)
    split = 5  # 舍弃前5个低频系数（含直流分量）
    # 截断高频部分并取幅度
    fft_high = np.abs(fft_coeffs[split:])
    return fft_high.tolist()

def hadamard_pre(data):
    # 哈达玛变换预处理
    n = len(data)
    # 调整长度为2的幂次（哈达玛矩阵要求）
    pad_len = 2 ** int(np.ceil(np.log2(n)))
    padded_data = np.pad(data, (0, pad_len - n), 'constant')
    # 执行哈达玛变换
    hadamard_matrix = hadamard(pad_len)
    transformed = np.dot(hadamard_matrix, padded_data)
    # 舍弃前1/4低频分量
    split = pad_len // 4
    return transformed[split:].tolist()[:n]  # 截断回原长度

def differential_quantization(data: list) -> str:
    """
    差分量化函数，将输入数组转为01序列
    """
    data = fft_pre(data)
    quantized_bits = []
    for i in range(len(data) - 1):
        if data[i + 1] >= data[i]:
            quantized_bits.append('1')
        else:
            quantized_bits.append('0')
    return ''.join(quantized_bits)




def dct_quantization(signal, block_size, selected_coeffs):
    n_blocks = len(signal) // block_size
    quantized_bits = []
    for i in range(n_blocks):
        # 截取当前块
        block = signal[i * block_size: (i + 1) * block_size]
        # 计算DCT
        dct_coeffs = dct(block, norm='ortho')

        # plt.figure(figsize=(10, 6))
        # plt.plot(dct_coeffs, label='Processed ', color='blue', marker='o')
        # plt.grid(True)
        # plt.legend()
        # plt.show()

        # 选择特定系数并量化
        for idx in selected_coeffs:
            coeff = dct_coeffs[idx]
            # 符号位+幅度阈值
            bit_sign = 1 if coeff >= 0 else 0
            bit_magnitude = 1 if abs(coeff) > 0.5 else 0  # 阈值
            quantized_bits.extend([bit_sign, bit_magnitude])

    return np.array(quantized_bits)

def _select_block_size(signal, max_size):
    """基于信号平稳性选择分块大小"""
    min_length = len(signal) // 2
    best_size = 8  # 默认值
    min_variance = float('inf')

    for size in [8, 16, 32]:
        if size > min_length: continue
        variances = []
        for i in range(0, len(signal), size):
            block = signal[i:i + size]
            if len(block) < size: break
            dct_coeffs = dct(block, norm='ortho')[1:]  # 排除DC分量
            variances.append(np.var(dct_coeffs))

        avg_var = np.mean(variances)
        if avg_var < min_variance:
            min_variance = avg_var
            best_size = size

    return best_size


def _select_coeffs(signal, block_size):
    """选择导频信号中最稳定的3个DCT系数"""
    n_blocks = len(signal) // block_size
    coeff_stability = np.zeros(block_size)

    for i in range(n_blocks):
        block = signal[i * block_size: (i + 1) * block_size]
        dct_coeffs = dct(block, norm='ortho')
        signs = (dct_coeffs >= 0).astype(int)
        coeff_stability += signs if i % 2 == 0 else -signs

    # 选择波动最小的系数（绝对值最小的累积值）
    stability_scores = np.abs(coeff_stability)
    return np.argsort(stability_scores)[:3].tolist()  # 选择最稳定的3个

def negotiate_parameters(pilot_signal, max_block_size=32):
    """双方独立执行的参数协商函数"""
    # 第一阶段：分块大小选择
    block_size = _select_block_size(pilot_signal, max_block_size)
    # 第二阶段：系数选择
    selected_coeffs = _select_coeffs(pilot_signal, block_size)
    return block_size, selected_coeffs

def calculate_mismatch_rate_with_length_check(seq1, seq2):
    len1, len2 = len(seq1), len(seq2)
    max_len = max(len1, len2)
    # 统计共同长度内的不一致次数
    common_mismatch = sum(c1 != c2 for c1, c2 in zip(seq1, seq2))
    # 计算长度差异带来的额外不匹配次数
    length_diff = abs(len1 - len2)
    total_mismatch = common_mismatch + length_diff
    return total_mismatch / max_len

def add_arrays(arr1, arr2):
    # 检查两个数组长度是否相同
    if len(arr1) != len(arr2):
        print(len(arr1),len(arr2))
        raise ValueError("数组长度不相等，无法相加！")
    result = []
    for i in range(len(arr1)):
        result.append(arr1[i] + arr2[i])
    return result


def plus_arrays(arr, subnum):
    # 检查两个数组长度是否相同
    result = []
    for i in range(len(arr)):
        result.append(arr[i] + subnum)

    return result


def min_arrays(arr, subnum):
    # 检查两个数组长度是否相同
    result = []
    for i in range(len(arr)):
        result.append(arr[i] - subnum)

    return result


def mod_array(arr, x):
    return np.mod(arr, x)

##################################################################NIST测试
import numpy as np
import math
import scipy.special

def frequency_test(bits):
    """频数测试（检测0/1分布平衡性）"""

    n = len(bits)
    s = sum(2 * bits - 1)  # +1 for 1, -1 for 0
    s_obs = abs(s) / math.sqrt(n)
    p_value = math.erfc(s_obs / math.sqrt(2))
    return p_value


def block_frequency_test(bits, block_size=8):
    """块内频数测试（检测局部均衡性，适配图片中的8字节分组）"""
    n = len(bits)
    if n < block_size:
        return 0.0

    num_blocks = n // block_size
    proportions = []

    for i in range(num_blocks):
        block = bits[i * block_size: (i + 1) * block_size]
        proportion = sum(block) / block_size
        proportions.append(proportion)

    chi_square = 4 * block_size * sum((p - 0.5) ** 2
    for p in proportions)
    p_value = scipy.special.gammaincc(num_blocks / 2, chi_square / 2)
    return p_value


def runs_test(bits):
    """游程测试（检测连续相同值的出现频率）"""
    n = len(bits)
    pi = sum(bits) / n
    if abs(pi - 0.5) >= 0.5:  # 提前终止条件
        return 0.0

    runs = 1
    for i in range(1, n):
        runs += 1 if bits[i] != bits[i - 1] else 0

    mu = 2 * n * pi * (1 - pi)
    variance = 4 * n * pi * (1 - pi) * (3 + 2 * pi - 2 * pi ** 2)
    sigma = math.sqrt(variance)

    z = (runs - mu) / sigma
    p_value = math.erfc(abs(z) / math.sqrt(2))
    return p_value


def longest_run_ones_test(bits):
    """块内最长连续1测试（符合NIST SP800-22标准）"""
    bits = np.asarray(bits, dtype=int)
    n = len(bits)

    # 确定分块策略
    if n >= 6272:
        block_size = 128
        thresholds = [4, 5, 6, 7, 8, 9]  # 128位块的阈值
        probabilities = [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]
    else:
        block_size = 8
        thresholds = [1, 2, 3, 4]  # 8位块的阈值
        probabilities = [0.2148, 0.3672, 0.2305, 0.1875]

    num_blocks = n // block_size
    counts = np.zeros(len(thresholds) + 1, dtype=int)  # 最后一位存放超限情况

    # 统计各块最长连续1
    for i in range(num_blocks):
        block = bits[i * block_size: (i + 1) * block_size]
        max_run = current = 0
        for bit in block:
            current = current * bit + bit  # 连续1计数器
            max_run = max(max_run, current)

        # 分类统计
        for j, thresh in enumerate(thresholds):
            if max_run <= thresh:
                counts[j] += 1
                break
        else:
            counts[-1] += 1

    # 计算卡方统计量
    chi_sq = sum((counts[i] - num_blocks * p) ** 2 / (num_blocks * p)
    for i, p in enumerate(probabilities))

    return scipy.special.gammaincc(len(probabilities) / 2, chi_sq / 2)


def dft_test(bits):
    """离散傅里叶变换测试（检测周期特性）"""
    n = len(bits)
    X = np.fft.fft(2 * np.array(bits) - 1)  # 转换为±1序列
    M = abs(X[:n // 2]) / math.sqrt(n)
    T = math.sqrt(3.0)  # 95%阈值

    N0 = 0.95 * n / 2
    N1 = sum(m < T for m in M)

    d = (N1 - N0) / math.sqrt(n * 0.95 * 0.05 / 4)
    return math.erfc(abs(d) / math.sqrt(2))


def linear_complexity_test(bits, block_size=500):
    """修复后的线性复杂度测试（NIST SP800-22标准）"""
    bits = np.asarray(bits, dtype=int)
    n = len(bits)

    # 输入验证
    if n < block_size * 4:  # 至少需要4个块
        raise ValueError(f"数据长度不足，至少需要{block_size * 4}位")

    num_blocks = n // block_size
    K = 6  # 分组数（根据NIST标准）

    # 步骤1：计算各块的线性复杂度
    complexities = []
    for i in range(num_blocks):
        block = bits[i * block_size: (i + 1) * block_size]
        L = berlekamp_massey(block)
        complexities.append(L)

    # 步骤2：计算理论期望值（基于NIST标准公式）
    mu = block_size / 2 + (9 + (-1) ** (block_size+1)) / 36 - (block_size / 3 + 2 / 9) / (2 ** block_size)
    sigma = math.sqrt(block_size * (1 / 36 - ((-1) ** block_size * (block_size / 3 + 2 / 9)) / (2 ** block_size)))

    # 步骤3：动态计算分组区间（避免空分组）
    min_L = min(complexities)
    max_L = max(complexities)
    bin_edges = np.linspace(min_L, max_L, K + 1)
    bins, _ = np.histogram(complexities, bins=bin_edges)

    # 步骤4：计算理论概率分布（正态分布近似）
    expected_probs = []
    for i in range(K):
        lower = bin_edges[i]
        upper = bin_edges[i + 1]
        prob = scipy.stats.norm.cdf(upper, mu, sigma) - scipy.stats.norm.cdf(lower, mu, sigma)
        expected_probs.append(prob)

    # 处理边缘情况：确保概率总和为1
    expected_probs = np.array(expected_probs)
    expected_probs /= expected_probs.sum()

    # 步骤5：计算卡方统计量（带防零处理）
    chi_sq = 0.0
    for i in range(K):
        observed = bins[i]
        expected = max(expected_probs[i] * num_blocks, 0.1)  # 防止零期望
        chi_sq += (observed - expected) ** 2 / expected

    # 步骤6：计算P值
    p_value = scipy.special.gammaincc((K - 1) / 2, chi_sq / 2)
    return p_value


def serial_test(bits, m=3):
    """序列测试（检测模式分布）"""
    n = len(bits)
    psi = [0.0, 0.0]

    for i in range(2):
        k = m - i
        counts = Counter(tuple(bits[j:j + k]) for j in range(n - k + 1))
        psi[i] = sum(val ** 2
        for val in counts.values())
        psi[i] = psi[i] * (2 ** k / n) - n

    delta = psi[0] - psi[1]
    return scipy.special.gammaincc(1, abs(delta)/2)


def approximate_entropy_test(bits_sequence):
    """近似熵测试（检测模式复杂性）"""
    n = len(bits_sequence)
    m = 3  # 固定模式长度（NIST标准）

    # 计算phi(m)
    patterns_m = [tuple(bits_sequence[i:i + m]) for i in range(n - m + 1)]
    counts_m = Counter(patterns_m)
    phi_m = sum(v * math.log(v / (n - m + 1)) for v in counts_m.values()) / (n - m + 1)

    # 计算phi(m+1)
    patterns_m1 = [tuple(bits_sequence[i:i + m + 1]) for i in range(n - m)]
    counts_m1 = Counter(patterns_m1)
    phi_m1 = sum(v * math.log(v / (n - m)) for v in counts_m1.values()) / (n - m)

    # 计算近似熵
    apen = phi_m - phi_m1

    # 计算P值（NIST标准公式）
    chi_square = 2 * n * (math.log(2) - apen)
    p_value = math.erfc(chi_square / 2)

    return p_value


def cumulative_sums_test(bits):
    """
    NIST累积和测试
    """
    # 转换为numpy数组并转为±1序列
    bits = np.array(bits, dtype=int)
    X = 2 * bits - 1  # 将0/1转为-1/+1
    S = np.cumsum(X)
    z_forward = np.max(np.abs(S)) / np.sqrt(len(bits))
    z_backward = np.max(np.abs(np.cumsum(X[::-1]))) / np.sqrt(len(bits))
    z = max(z_forward, z_backward)
    sum_terms = 0.0
    for k in range(-5, 6):
        term1 = math.erfc((4 * k + 1) * z / math.sqrt(2))
        term2 = math.erfc((4 * k - 1) * z / math.sqrt(2))
        sum_terms += ((-1) ** k) * (term1 - term2)

    p_value = 1 - sum_terms
    return p_value


def non_overlapping_test(bits, template="0001"):
    """非重叠模板匹配测试"""
    m = len(template)
    n = len(bits)
    W = [int(c) for c in template]

    # 统计匹配次数
    count = 0
    i = 0
    while i <= n - m:
        if bits[i:i + m] == W:
            count += 1
            i += m
        else:
            i += 1

    mu = (n - m + 1) / 2 ** m
    var = n * (1 / 2 ** m - (2 * m -1) / 2 ** (2 * m))
    chi_sq = (count - mu) ** 2 / var

    return scipy.special.gammaincc(0.5, chi_sq / 2)


# 辅助函数
def berlekamp_massey(sequence):
    """计算线性复杂度（BMA算法）"""
    n = len(sequence)
    C, B, L, m = [1], [1], 0, 1

    for N in range(n):
        d = sequence[N]
        for i in range(1, L + 1):
            d ^= C[i] & sequence[N - i]

        if d == 1:
            T = C.copy()
            C += [0] * (N + 1 - len(C))
            for i in range(len(B)):
                C[N - m + i] ^= B[i]

            if L <= N // 2:
                L = N + 1 - L
                m = N
                B = T

    return L

def apply_nist_suite(bits, alpha=0.01):
    """执行完整的NIST测试套件"""
    tests = [
        ("Frequency", lambda: frequency_test(bits)),
        ("Block Frequency", lambda: block_frequency_test(bits)),
        ("Runs", lambda: runs_test(bits)),
        ("Longest Run", lambda: longest_run_ones_test(bits)),
        ("DFT", lambda: dft_test(bits)),
        ("Linear Complexity", lambda: linear_complexity_test(bits)),
        ("Serial", lambda: serial_test(bits)),
        ("Approximate Entropy", lambda: calculate_entropy(bits)),
        ("Cumulative Sums", lambda: cumulative_sums_test(bits)),
        ("Non-overlapping Template", lambda: non_overlapping_test(bits))
    ]

    print(f"NIST测试报告（样本量：{len(bits)} bits）")
    print("=" * 50)
    results = {}

    for name, test in tests:
        try:
            p_value = test()
            status = "通过" if p_value >= alpha else "未通过"
            results[name] = (p_value, status)
            print(f"{name:<25} | P值: {p_value:.6f} | {status}")
        except Exception as e:
            print(f"{name} 测试失败: {str(e)}")
            results[name] = (None, "Error")

    return results

rplusp_alice = np.zeros(130)
rplusp_bob   = np.zeros(130)
power_alice = np.zeros(130)
power_bob = np.zeros(130)
rssi_alice = np.zeros(130)
rssi_bob = np.zeros(130)
alice_random_numbers = np.zeros(130)
bob_random_numbers = np.zeros(130)
eve_random_numbers = np.zeros(130)
rssieve_alice = np.zeros(130)
rssieve_bob = np.zeros(130)

def moving_average(data, window_size):
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')

# 窗口大小
window_size = 5

# 移动平均后RSSI数据
rplusp_eve = add_arrays(rssieve_alice,rssieve_bob)
rplusp_alice_smoothed = moving_average(rplusp_alice, window_size)
rplusp_bob_smoothed = moving_average(rplusp_bob, window_size)
rplusp_eve_smoothed = moving_average(rplusp_eve, window_size)

print(f"eve=the sum of Alice's and Bob's RSSI:{rplusp_eve}")

correlation_matrix_original = np.corrcoef(rplusp_alice, rplusp_bob)
correlation_original = correlation_matrix_original[0, 1]
# 平滑后相关系数
correlation_matrix_smoothed = np.corrcoef(rplusp_alice_smoothed, rplusp_bob_smoothed)
correlation_smoothed = correlation_matrix_smoothed[0, 1]
correlation_matrix_smoothed_eve =np.corrcoef(rplusp_bob_smoothed, rplusp_eve_smoothed)
correlation_smoothed_eve = correlation_matrix_smoothed_eve[0, 1]

plt.figure(figsize=(12, 6))

# 原始 rssi
plt.plot(rplusp_alice, label='Original RSSI Alice', linestyle='--', marker='o', alpha=0.5)
plt.plot(rplusp_bob, label='Original RSSI Bob', linestyle='--', marker='x', alpha=0.5)

# 滤波 rssi
plt.plot(rplusp_alice_smoothed, label='Smoothed RSSI Alice', color='blue', marker='o')
plt.plot(rplusp_bob_smoothed, label='Smoothed RSSI Bob', color='orange', marker='x')


plt.legend()
plt.title(f'Original correlation:{correlation_original}, Smoothed correlation:{correlation_smoothed}')
plt.xlabel('Packet Number')
plt.ylabel('RSSI (dBm)')
plt.grid()
plt.show()

plt.figure(figsize=(12, 6))

# 原始 rssi
plt.plot(rplusp_eve, label='Original RSSI Eve', linestyle='--', marker='o', alpha=0.5)
plt.plot(rplusp_bob, label='Original RSSI Bob', linestyle='--', marker='x', alpha=0.5)

# 滤波 rssi
plt.plot(rplusp_eve_smoothed, label='Smoothed RSSI Eve', color='blue', marker='o')
plt.plot(rplusp_bob_smoothed, label='Smoothed RSSI Bob', color='orange', marker='x')
plt.legend()
plt.title(f' Smoothed correlation:{correlation_smoothed_eve}')
plt.xlabel('Packet Number')
plt.ylabel('RSSI (dBm)')
plt.grid()
plt.show()


###均值量化
mean_alice1,threshold1_a, threshold2_a = quantize_rssi(rplusp_alice)
mean_bob1,threshold1_b, threshold2_b  = quantize_rssi(rplusp_bob)

mean_alice = quantized_to_binary(mean_alice1)
mean_bob = quantized_to_binary(mean_bob1)
BER_mean = calculate_mismatch_rate_with_length_check(mean_alice, mean_bob)

print(f"均值量化Alice：{mean_alice}")
print(f"均值量化__Bob：{mean_bob}")
print(f"均值量化误码率：{BER_mean}")
###差分量化
diff_alice1 = differential_quantization(rplusp_alice)
diff_bob1  = differential_quantization(rplusp_bob)


BER_diff = calculate_mismatch_rate_with_length_check(diff_alice1, diff_bob1)

print(f"差分量化Alice：{diff_alice1}")
print(f"差分量化__Bob：{diff_bob1}")
print(f"差分量化误码率：{BER_diff}")

# corrected_bob = galois_bch_correction(dct_alice, dct_bob)
corrected_bob = galois_bch_correction(mean_alice, mean_bob)
print(corrected_bob)

BER = calculate_mismatch_rate_with_length_check(mean_alice, corrected_bob)
print(f"误码率(BER): {BER:.4f}")


# 再DCT量化
dct_alice = dct_quantization(rplusp_alice_smoothed, block_size=8, selected_coeffs=[4,5,6,7])
dct_bob = dct_quantization(rplusp_bob_smoothed, block_size=8, selected_coeffs=[4,5,6,7])
dct_eve = dct_quantization(rplusp_eve_smoothed, block_size=8, selected_coeffs=[4,5,6,7])
print("Raw Key:", dct_alice)
print("Raw Key:", dct_bob)
print("Eve Key:", dct_eve)

plt.figure(figsize=(10, 3))
plt.plot(list(dct_alice), label='Alice', color='#dcb430', marker='o')
plt.plot(list(dct_bob), label='Bob', color='#649635', marker='x')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()

plt.figure(figsize=(10, 3))
plt.plot(list(dct_alice), label='Alice', color='#299D92', marker='o')
# plt.plot(list(dct_bob), label='Bob', color='#649635', marker='x')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()


plt.figure(figsize=(10, 3))
# plt.plot(list(dct_alice), label='Alice', color='#dcb430', marker='o')
plt.plot(list(dct_bob), label='Bob', color='#299D92', marker='o')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()



pilot_alice = rplusp_alice
pilot_bob = rplusp_bob
pilot_eve = rplusp_eve
alice_block_size, alice_coeffs = negotiate_parameters(pilot_alice)
bob_block_size, bob_coeffs = negotiate_parameters(pilot_bob)
eve_block_size, eve_coeffs = negotiate_parameters(pilot_eve)

print(alice_block_size, alice_coeffs)
print(bob_block_size, bob_coeffs)
print(eve_block_size, eve_coeffs)


coeffs=[0,4,6]

dct_alice = dct_quantization(rplusp_alice_smoothed, alice_block_size, coeffs)
dct_bob = dct_quantization(rplusp_bob_smoothed, bob_block_size, coeffs)
dct_eve = dct_quantization(rplusp_eve_smoothed,eve_block_size, coeffs)
print(dct_alice)
print(dct_bob)
dct_BER=calculate_mismatch_rate_with_length_check(dct_alice,dct_bob)
dct_BER_eve=calculate_mismatch_rate_with_length_check(dct_eve,dct_bob)
print(f"误码率(BER): {dct_BER:.4f}")
print(f"窃听误码率(BER): {dct_BER_eve:.4f}")

#纠错
# corrected_bob = galois_bch_correction(dct_alice, dct_bob)
corrected_bob = galois_bch_correction(dct_alice, dct_bob)
corrected_eve = galois_bch_correction(dct_bob, dct_eve)

print(f"纠错后bob: {corrected_bob}")
print(f"纠错后eve: {corrected_eve}")

BER = calculate_mismatch_rate_with_length_check(dct_alice, corrected_bob)
print(f"纠错后误码率(BER): {BER:.4f}")
BER_eve = calculate_mismatch_rate_with_length_check(dct_eve, corrected_bob)
print(f"纠错后误码率(BER): {BER_eve:.4f}")

plt.figure(figsize=(10, 3))
plt.plot(list(dct_alice), label='Alice', color='#27736F', marker='o')
# plt.plot(list(dct_bob), label='Bob', color='#649635', marker='x')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()


plt.figure(figsize=(10, 3))
# plt.plot(list(dct_alice), label='Alice', color='#dcb430', marker='o')
plt.plot(list(corrected_bob), label='Bob', color='#27736F', marker='o')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()

#密钥熵计算
corrected_bits = corrected_bob
entropy_before_hash = calculate_entropy(corrected_bits)
print(f"隐私放大前熵: {entropy_before_hash:.2f} bits/bit")

# balenced_bits = modify_consecutive(corrected_bits, 2)
balenced_bits_bob = modify_consecutive_enhanced(corrected_bits,2)
balenced_bits_alice = modify_consecutive_enhanced(dct_alice,2)

sync_rand_alice = SyncRandom(seed=0x8)
sync_rand_bob = SyncRandom(seed=0x8)
balenced_bits_bob_sync = modify_consecutive_sync(corrected_bits,2,sync_rand_bob)
balenced_bits_alice_sync = modify_consecutive_sync(dct_alice,2,sync_rand_alice)

entropy_before_hash = calculate_entropy(balenced_bits_bob)
entropy_before_hash_sync = calculate_entropy(balenced_bits_bob_sync)

plt.figure(figsize=(10, 3))
plt.plot(list(balenced_bits_alice_sync), label='Alice', color='#264653', marker='o')
# plt.plot(list(dct_bob), label='Bob', color='#649635', marker='x')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()


plt.figure(figsize=(10, 3))
# plt.plot(list(dct_alice), label='Alice', color='#dcb430', marker='o')
plt.plot(list(balenced_bits_bob_sync), label='Bob', color='#264653', marker='o')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()


print(f"平衡熵序列: {balenced_bits_bob}")
print(f"平衡熵: {entropy_before_hash:.2f} bits/bit")
#不一致率
FINAL_BER = calculate_mismatch_rate_with_length_check(balenced_bits_alice, balenced_bits_bob)
print(f"误码率(BER): {FINAL_BER:.4f}")


print(f"sync平衡熵: {entropy_before_hash_sync:.2f} bits/bit")
#不一致率
FINAL_BER_sync = calculate_mismatch_rate_with_length_check(balenced_bits_alice_sync, balenced_bits_bob_sync)
print(f"sync误码率(BER): {FINAL_BER_sync:.4f}")
print(f"sync平衡熵序列: {balenced_bits_alice_sync}")
print(f"sync平衡熵序列: {balenced_bits_bob_sync}")



plt.figure(figsize=(10, 3))
plt.plot(list(dct_alice), label='Alice', color='#264653', marker='o')
# plt.plot(list(dct_bob), label='Bob', color='#649635', marker='x')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()


plt.figure(figsize=(10, 3))
# plt.plot(list(dct_alice), label='Alice', color='#dcb430', marker='o')
plt.plot(list(balenced_bits_alice_sync), label='Balenced_Alice', color='#264653', marker='o')
# plt.plot(list(rssi_bob_bin), label='Quantized Bob RSSI (Binary)', color='red', marker='x')
plt.xlabel('Packet Number')
plt.ylabel('Binary Value ')
plt.title('Binary Quantized RSSI')
plt.grid(True)

plt.show()

# NIST
def gf2_to_int(gf2_array):
    """安全转换GF2数组到整数数组"""
    return gf2_array.view(np.ndarray).astype(int)
# 执行测试套件
int_data_sync = gf2_to_int(balenced_bits_bob_sync)
test_results = apply_nist_suite(int_data_sync)


# 执行测试套件
int_data = gf2_to_int(balenced_bits_bob)
test_results = apply_nist_suite(int_data)

#保密增强
def privacy_amplification(shared_bits, output_length=128, hash_function='sha256'):
    """隐私放大函数，将共享比特压缩为最终密钥"""
    # 将GF2数组转为普通比特数组
    bits = shared_bits.view(np.ndarray).astype(int)

    # 转换为字节（使用之前的函数）
    byte_data = bits_to_bytes(bits)

    # 选择哈希算法
    if hash_function == 'sha256':
        hasher = hashlib.sha256()
    elif hash_function == 'sha3_256':
        hasher = hashlib.sha3_256()
    else:
        raise ValueError("Unsupported hash function")

    # 计算哈希值
    hasher.update(byte_data)
    full_digest = hasher.digest()

    # 截取指定长度（单位：字节）
    key_bytes = full_digest[:output_length // 8]

    # 转换为十六进制字符串
    return key_bytes.hex()

# 在代码最后添加隐私放大步骤（假设双方已同步）
final_key_alice = privacy_amplification(balenced_bits_alice_sync)
final_key_bob = privacy_amplification(balenced_bits_bob_sync)

print(f"Alice Final Key: {final_key_alice}")
print(f"Bob Final Key:   {final_key_bob}")
print(f"Keys Match: {final_key_alice == final_key_bob}")

def generate_key_qrcode(key_str, filename="key_qrcode.png", version=1):
    """
    生成包含密钥信息的二维码
    参数：
        key_str: 密钥字符串
        filename: 保存文件名
        version: 1-40
    """
    # 创建QRCode对象
    qr = qrcode.QRCode(
        version=version,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 高容错率
        box_size=10,
        border=4,
    )

    # 添加数据
    qr.add_data(key_str)
    qr.make(fit=True)

    # 生成图像（自定义颜色）
    img = qr.make_image(fill_color="navy", back_color="white")  # 深蓝色填充

    # 保存文件
    img.save(filename)
    return img


# 生成双方密钥的二维码（假设双方密钥已同步）
if final_key_alice == final_key_bob:
    print("生成同步密钥码...")
    img = generate_key_qrcode(final_key_alice, "shared_key_qrcode.png")
    print("密钥码生成成功")
    # 可视化显示
    plt.figure(figsize=(6, 6))
    plt.imshow(img, cmap='gray')
    plt.title("Shared Secret Key QR Code\n(Physical Layer Security)", pad=20)
    plt.axis('off')
    plt.show()
else:
    print("警告：双方密钥不一致，无法生成二维码！")
