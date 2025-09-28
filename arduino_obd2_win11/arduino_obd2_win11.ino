#include <mcp_can.h>
#include <SPI.h>

#define CAN0_CS 53
#define CAN0_INT 2
MCP_CAN CAN0(CAN0_CS);

unsigned long lastDTCRequest = 0;
unsigned long lastRPMRequest = 0;
unsigned long lastSpeedRequest = 0;
unsigned long lastLoadRequest = 0;
unsigned long lastFuelRequest = 0;
unsigned long lastBoostRequest = 0;
unsigned long lastVoltageRequest = 0;

bool canInitialized = false;
bool obdConnected = false;
int dtcCount = 0;
int engineRPM = 0;
int vehicleSpeed = 0;
int engineLoad = 0;
int fuelLevel = 0;
int boostPressure = 0;
int batteryVoltage = 0;

unsigned long rxId;
unsigned char len;
unsigned char rxBuf[8];

const int BATTERY_PIN = A0;  // Analoger Eingang für Spannungsteiler
const float VOLTAGE_DIVIDER_RATIO = (100.0 + 10.0) / 10.0;  // R1=100k, R2=10k


void setup() {
  Serial.begin(115200);
  while (CAN0.begin(MCP_STDEXT, CAN_500KBPS, MCP_8MHZ) != CAN_OK) delay(200);
  CAN0.setMode(MCP_NORMAL);
  canInitialized = true;
}

void loop() {
  unsigned long now = millis();
  if (!canInitialized) return;
  if (!obdConnected) testOBDConnection();
  if (now - lastDTCRequest > 3000) { requestDTCCount(); lastDTCRequest = now; }
  if (now - lastRPMRequest > 500) { requestEngineRPM(); lastRPMRequest = now; }
  if (now - lastSpeedRequest > 500) { requestVehicleSpeed(); lastSpeedRequest = now; }
  if (now - lastLoadRequest > 500) { requestEngineLoad(); lastLoadRequest = now; }
  if (now - lastFuelRequest > 1000) { requestFuelLevel(); lastFuelRequest = now; }
  if (now - lastBoostRequest > 1000) { requestBoostPressure(); lastBoostRequest = now; }
  if (now - lastVoltageRequest > 5000) { requestBatteryVoltage(); lastVoltageRequest = now; }
  processSerialCommands();
}

void testOBDConnection() {
  unsigned char req[]={0x02,0x01,0x00,0,0,0,0,0};
  CAN0.sendMsgBuf(0x7DF,0,8,req);
  if(waitForResponse(0x7E8,500)&&rxBuf[1]==0x41&&rxBuf[2]==0x00) obdConnected=true;
}

void requestDTCCount() {
  if(!obdConnected) return;
  unsigned char req[]={0x02,0x01,0x01,0,0,0,0,0};
  CAN0.sendMsgBuf(0x7DF,0,8,req);
  if(waitForResponse(0x7E8,300)&&rxBuf[1]==0x41&&rxBuf[2]==0x01) {
    int c=rxBuf[3]&0x7F;
    if(c!=dtcCount){dtcCount=c;Serial.print("DTC_COUNT:");Serial.println(dtcCount);}
  }
}

void requestEngineRPM() {
  if(!obdConnected) return;
  unsigned char req[]={0x02,0x01,0x0C,0,0,0,0,0};
  CAN0.sendMsgBuf(0x7DF,0,8,req);
  if(waitForResponse(0x7E8,200)&&rxBuf[1]==0x41&&rxBuf[2]==0x0C) {
    int r=((rxBuf[3]*256)+rxBuf[4])/4;
    if(abs(r-engineRPM)>10){engineRPM=r;Serial.print("RPM:");Serial.println(engineRPM);}
  }
}

void requestVehicleSpeed() {
  if(!obdConnected) return;
  unsigned char req[]={0x02,0x01,0x0D,0,0,0,0,0};
  CAN0.sendMsgBuf(0x7DF,0,8,req);
  if(waitForResponse(0x7E8,200)&&rxBuf[1]==0x41&&rxBuf[2]==0x0D) {
    int s=rxBuf[3];
    if(s!=vehicleSpeed){vehicleSpeed=s;Serial.print("SPEED:");Serial.println(vehicleSpeed);}
  }
}

void requestEngineLoad() {
  if(!obdConnected) return;
  unsigned char req[]={0x02,0x01,0x04,0,0,0,0,0};
  CAN0.sendMsgBuf(0x7DF,0,8,req);
  if(waitForResponse(0x7E8,200)&&rxBuf[1]==0x41&&rxBuf[2]==0x04) {
    int l=(rxBuf[3]*100)/255;
    if(l!=engineLoad){engineLoad=l;Serial.print("LOAD:");Serial.println(engineLoad);}
  }
}

void requestFuelLevel() {
  if(!obdConnected) return;
  unsigned char req[]={0x02,0x01,0x2F,0,0,0,0,0};
  CAN0.sendMsgBuf(0x7DF,0,8,req);
  if(waitForResponse(0x7E8,200)&&rxBuf[1]==0x41&&rxBuf[2]==0x2F) {
    int f=(rxBuf[3]*100)/255;
    if(f!=fuelLevel){fuelLevel=f;Serial.print("FUEL:");Serial.println(fuelLevel);}
  }
}

void requestBoostPressure() {
  if(!obdConnected) return;
  unsigned char req[]={0x02,0x01,0x0B,0,0,0,0,0};
  CAN0.sendMsgBuf(0x7DF,0,8,req);
  if(waitForResponse(0x7E8,200)&&rxBuf[1]==0x41&&rxBuf[2]==0x0B) {
    int b=rxBuf[3]; 
    if(b!=boostPressure){boostPressure=b;Serial.print("BOOST:");Serial.println(boostPressure);}
  }
}

void requestBatteryVoltage() {
  int raw = analogRead(BATTERY_PIN);
  float volts = (raw / 1023.0) * 5.0 * VOLTAGE_DIVIDER_RATIO;
  int batt = int(volts * 10);  // z.B. 125 => 12.5V
  if (batt != batteryVoltage) {
    batteryVoltage = batt;
    Serial.print("BATT:");
    Serial.print(batt / 10);
    Serial.print('.');
    Serial.println(batt % 10);
  }
}


bool waitForResponse(unsigned long id,unsigned int t) {
  unsigned long s=millis();
  while(millis()-s<t){
    if(CAN0.checkReceive()==CAN_MSGAVAIL){
      CAN0.readMsgBuf(&rxId,&len,rxBuf);
      if(rxId>=0x7E8&&rxId<=0x7EF) return true;
    }
  }
  return false;
}

void clearDTCs() {
  unsigned char cmd[]={0x01,0x04,0,0,0,0,0,0};
  CAN0.sendMsgBuf(0x7DF,0,8,cmd);
  delay(1000);
  Serial.println("DTC_GELOESCHT");
}

void processSerialCommands() {
  if(Serial.available()){
    String cmd=Serial.readStringUntil('\n');cmd.trim();
    if(cmd=="CLEAR_DTC") clearDTCs();
  }
}
