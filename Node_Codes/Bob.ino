#include "LoRaWan_APP.h"
#include "Arduino.h"
#include <Wire.h>               
#include "HT_SSD1306Wire.h"


namespace MyDisplay {
  SSD1306Wire display(0x3c,500000, SDA_OLED, SCL_OLED, GEOMETRY_128_64,RST_OLED);
}

#define RF_FREQUENCY                                865000000 // Hz

//#define TX_OUTPUT_POWER                             5        // dBm

#define LORA_BANDWIDTH                              0         // [0: 125 kHz,
                                                              //  1: 250 kHz,
                                                              //  2: 500 kHz,
                                                              //  3: Reserved]
#define LORA_SPREADING_FACTOR                       7         // [SF7..SF12]
#define LORA_CODINGRATE                             1         // [1: 4/5,
                                                              //  2: 4/6,
                                                              //  3: 4/7,
                                                              //  4: 4/8]
#define LORA_PREAMBLE_LENGTH                        8         // Same for Tx and Rx
#define LORA_SYMBOL_TIMEOUT                         0         // Symbols
#define LORA_FIX_LENGTH_PAYLOAD_ON                  false
#define LORA_IQ_INVERSION_ON                        false


#define BUFFER_SIZE                                 30 // Define the payload size here
#define MaxRssiNum                                  300
#define RX_TIMEOUT_VALUE                            5000
#define power_level                                 6
#define RX_TIMEOUT_VALUE                            3000
#define Maxmatrix                                   129

char txpacket[BUFFER_SIZE];
char rxpacket[BUFFER_SIZE];

static RadioEvents_t RadioEvents;
void OnTxDone( void );
void OnTxTimeout( void );
void OnRxDone( uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr );

typedef enum
{
    LOWPOWER,
    STATE_RX,
    STATE_TX
}States_t;

int16_t txNumberBob;
States_t state;
bool sleepMode = false;
int16_t Rssi,rxSize;
///////////////////////////////////////////////
int16_t TX_power[power_level] = {5,6,7,8,9,10};             //功率选择                        //6个挡位
int16_t current_power_num=0;
/////////////////////////////////////////////////
int lastpower=-1;
int randompower=0;
unsigned long rxStartTime;
bool timeout = false;
int combined_value_b;
int powerTrend = 0;
int next_power;
bool MatrixFull=false;
int RplusP[Maxmatrix];
int powermatrix[Maxmatrix];
int rssmatrix[Maxmatrix];


void setup() {
    Serial.begin(115200);
    Mcu.begin();

    MyDisplay::display.init();
    MyDisplay::display.clear();
    MyDisplay::display.display();
    MyDisplay::display.setContrast(255);
    MyDisplay::display.setTextAlignment(TEXT_ALIGN_LEFT);
    MyDisplay::display.clear();
    MyDisplay::display.display();


    txNumberBob=0;
    Rssi=0;

    RadioEvents.TxDone = OnTxDone;
    RadioEvents.TxTimeout = OnTxTimeout;
    RadioEvents.RxDone = OnRxDone;

    Radio.Init( &RadioEvents );
    Radio.SetChannel( RF_FREQUENCY );
    Radio.SetTxConfig( MODEM_LORA, TX_power[current_power_num], 0, LORA_BANDWIDTH,
                                   LORA_SPREADING_FACTOR, LORA_CODINGRATE,
                                   LORA_PREAMBLE_LENGTH, LORA_FIX_LENGTH_PAYLOAD_ON,
                                   true, 0, 0, LORA_IQ_INVERSION_ON, 3000 );

    Radio.SetRxConfig( MODEM_LORA, LORA_BANDWIDTH, LORA_SPREADING_FACTOR,
                                   LORA_CODINGRATE, 0, LORA_PREAMBLE_LENGTH,
                                   LORA_SYMBOL_TIMEOUT, LORA_FIX_LENGTH_PAYLOAD_ON,
                                   0, true, 0, 0, LORA_IQ_INVERSION_ON, true );
    
    Serial.printf("Bob BEGIN\n");
    state=STATE_RX;
}




void loop() 
{
  switch(state)
  {
    case STATE_TX:
      delay(100);
      if(txNumberBob >= 128)
      {
      MatrixFull=true;
      }

      //dual limit
            if (lastpower == -1) {
                randomSeed(micros() + analogRead(0));
                
                current_power_num = random(2, power_level-1); // Start from 1 to avoid getting stuck at 0
                lastpower = current_power_num; // Initialize lastPower for the first iteration
            } else {

                do {
                    randomSeed(micros());
                    next_power = random(power_level);

                    // Single limit: ensure power level change is at most 1
                } while ((abs(next_power - lastpower) > 2) ||
                         // Double limit: avoid continuous increase or decrease
                         ((powerTrend == 1 && next_power > lastpower) ||
                          (powerTrend == -1 && next_power < lastpower)));
                current_power_num = next_power;
            }

            // Update power trend
            if (current_power_num > lastpower) {
                powerTrend = 1;  // Increasing trend
            } else if (current_power_num < lastpower) {
                powerTrend = -1; // Decreasing trend
            } else {
                powerTrend = 0;  // No change
            }
      lastpower = current_power_num;
      combined_value_b = TX_power[current_power_num] + Rssi;

      if(MatrixFull)
      {
        printArray(RplusP, Maxmatrix);
        printArray(powermatrix, Maxmatrix);
        printArray(rssmatrix, Maxmatrix);
        Serial.printf("BOB\n");
        MatrixFull=false;
        txNumberBob=0;
      }
      else
      {
        RplusP[txNumberBob]=combined_value_b;
        powermatrix[txNumberBob] = TX_power[current_power_num];
        rssmatrix[txNumberBob] = Rssi;
        txNumberBob++;
      }




//////////////////////////////////////////////////////////////////////////////////////////////////////////////
      Radio.SetTxConfig( MODEM_LORA, TX_power[current_power_num], 0, LORA_BANDWIDTH,
                                    LORA_SPREADING_FACTOR, LORA_CODINGRATE,
                                    LORA_PREAMBLE_LENGTH, LORA_FIX_LENGTH_PAYLOAD_ON,
                                    true, 0, 0, LORA_IQ_INVERSION_ON, 3000 ); 
//////////////////////////////////////////////////////////////////////////////////////////////////////////////
 



      sprintf(txpacket,"bob @%d",txNumberBob);
      Radio.Send( (uint8_t *)txpacket, strlen(txpacket) );
      state=LOWPOWER;
      break;
    case STATE_RX:
      Radio.Rx( 0 );
      state=LOWPOWER;
      break;
    case LOWPOWER:
      Radio.IrqProcess( );
      break;
    default:
      break;
  }
}





void OnTxDone( void )
{

  state=STATE_RX;
}

void OnTxTimeout( void )
{
    Radio.Sleep( );
    Serial.print("TX Timeout......");
    state=STATE_TX;
}

void OnRxDone( uint8_t *payload, uint16_t size, int16_t rssi, int8_t snr )
{
  
    if (strcmp(rxpacket, "RESET") == 0) {
    handleReset();  // Call the reset function when receiving "RESET" signal
  }

    Rssi=rssi;
    rxSize=size;
    memcpy(rxpacket, payload, size );
    rxpacket[size]='\0';
    Radio.Sleep( );



    //lastpower=atoi(rxpacket);
    rxStartTime = millis();
    MyDisplay::display.clear();
    MyDisplay::display.drawString(0, 0, "Received Packet");
    MyDisplay::display.drawString(0, 15, "Alicenum: " + String(rxpacket));
    MyDisplay::display.drawString(0, 30, "Bobnum  : " + String(txNumberBob));
    MyDisplay::display.display();

    //Serial.printf(" %d,",Rssi);
    rxStartTime = millis();
    state=STATE_TX;
}
void printArray(int arr[], int size) {
  for (int i = 0; i < size; i++) {
    Serial.printf(" %d,", arr[i]);
  }
  Serial.printf(" \n");
}


void handleReset() {
  // 复位操作：重置变量、清空数据等
  Serial.println("Reset signal received. Resetting system...");

  // 清除 OLED 屏幕显示
  MyDisplay::display.clear();
  MyDisplay::display.drawString(0, 0, "RESET SIGNAL RECEIVED");
  MyDisplay::display.drawString(0, 15, "System Resetting...");
  MyDisplay::display.display();

  // 仅重置与功率调节无关的变量
  Serial.println("Resetting power-related variables...");
  // 清除或重置需要复位的变量
  randompower = 0;   // 重置随机功率选择的状态
  // 这里不要重置 txNumberBob，以保持传输次数的一致性
  txNumberBob = 0;  
  lastpower = -1;    // 重置 lastpower 为 -1，保证首次使用随机功率选择
  powerTrend = 0;    // 重置功率趋势（如果有的话）
  
  // 如果需要清除其他缓存或数据，可以在这里进行
  // memset(rssmatrix, 0, sizeof(rssmatrix));  // 清空 RSSI 数据矩阵

  delay(500);  // 显示复位状态，等待几秒钟再开始重新接收

  // 复位 LoRa 设备的状态
  Radio.Sleep();  // 让 LoRa 设备进入休眠模式
  Radio.Rx(0);    // 重新启动接收模式
}
