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
#define RX_TIMEOUT_VALUE                            3000
#define power_level                                 6
#define Maxmatrix                                   129
#define RESET_BUTTON_PIN                            7

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

int16_t txNumberAlice;
States_t state;

int16_t Rssi,rxSize;
/////////////////////////////////////////////////
int16_t TX_power[power_level] = {10,10,10,10,10,10};             //功率选择                        //6个挡位
int16_t current_power_num=0;
/////////////////////////////////////////////////

int lastpower=-1;
int randompower=0;
unsigned long rxStartTime;
bool timeout = false;
int combined_value_a;
int powerTrend = 0;
int next_power;
int RplusP[Maxmatrix];
int powermatrix[Maxmatrix];
int rssmatrix[Maxmatrix];
bool MatrixFull=false;
bool resetButtonState = false;
bool lastResetButtonState = false;
bool sleepMode = false;
bool TIMEOUT = false;


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


    txNumberAlice=0;
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
    
    Serial.printf("ALICE BEGIN\n");
    state=STATE_TX;
}




void loop() 
{
  // 超时重发
   if (millis() - rxStartTime > RX_TIMEOUT_VALUE) {
     TIMEOUT = true;    //超时重传
     rxStartTime = millis();
     Serial.println("no packet received for a few seconds, switching to TX");
     state = STATE_TX;  // switch to TX state
   }



 resetButtonState = digitalRead(RESET_BUTTON_PIN) == LOW; // 按钮按下为 LOW

    // 如果按钮从未按下到按下的状态发生变化，则发送复位信号
    if (resetButtonState && !lastResetButtonState) {
        sendResetSignal();  // 发送复位信号
    }

    lastResetButtonState = resetButtonState;  // 保存按钮状态



  switch(state)
  {
    case STATE_TX:
      delay(100);

      if(txNumberAlice >= 128)
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




//////////////////////////////////////////////////////////////////////////////////////////////////////////////
      Radio.SetTxConfig( MODEM_LORA, TX_power[current_power_num], 0, LORA_BANDWIDTH,
                                    LORA_SPREADING_FACTOR, LORA_CODINGRATE,
                                    LORA_PREAMBLE_LENGTH, LORA_FIX_LENGTH_PAYLOAD_ON,
                                    true, 0, 0, LORA_IQ_INVERSION_ON, 3000 ); 
//////////////////////////////////////////////////////////////////////////////////////////////////////////////
 




      sprintf(txpacket,"alice @%d",txNumberAlice);
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
    Rssi=rssi;
    rxSize=size;
    memcpy(rxpacket, payload, size );
    rxpacket[size]='\0';
    Radio.Sleep( );
    combined_value_a = TX_power[current_power_num] + Rssi;


    MyDisplay::display.clear();
    MyDisplay::display.drawString(0, 0, "Received Packet");
    MyDisplay::display.drawString(0, 15, "Rssi: " + String(Rssi));
    MyDisplay::display.drawString(0, 30, "Bobnum  : " + String(rxpacket));
    MyDisplay::display.drawString(0, 45, "Alicenum: " + String(txNumberAlice));
    MyDisplay::display.display();

    if(MatrixFull)
    {
      printArray(RplusP, Maxmatrix);
      printArray(powermatrix, Maxmatrix);
      printArray(rssmatrix, Maxmatrix);
      Serial.printf("ALICE\n");
      MatrixFull=false;
      txNumberAlice=0;
    }
    else
    {
      RplusP[txNumberAlice] = combined_value_a;
      powermatrix[txNumberAlice] = TX_power[current_power_num];
      rssmatrix[txNumberAlice] = Rssi;
      txNumberAlice++;
    }

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

void sendResetSignal() {
    // 发送复位信号给Bob
    char resetMessage[] = "RESET";
    Radio.Send((uint8_t*)resetMessage, strlen(resetMessage));
    Serial.println("Reset signal sent to Bob.");

    // 在OLED显示屏上显示发送信息
    MyDisplay::display.clear();
    MyDisplay::display.drawString(0, 0, "Sending Reset Signal");
    MyDisplay::display.drawString(0, 15, "To Bob...");
    MyDisplay::display.display();
}






