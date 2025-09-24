import serial
import serial.tools.list_ports
import threading
import tkinter as tk
from tkinter import messagebox, Canvas
import time

SERIAL_PORT = "COM3"
BAUDRATE = 115200
DATA_INTERVAL = 0.05  # in Sekunden

class OBDGui:
    def __init__(self, root):
        self.root = root
        root.title("OBD2 Scanner - VAG/FIAT")
        root.geometry("1200x1080")
        root.configure(bg='#2c3e50')
        root.resizable(False, False)

        self.ser = None
        self.running = True
        self.current_view_frame = None  # Referenz auf aktuellen Frame

        # Live-Daten-Puffer
        self.current_rpm = 0
        self.dtc_count = 0
        self.current_speed = 0
        self.current_load = 0
        self.current_boost = 0
        self.current_fuel = 0
        self.current_batt = 0.0

        # Status-Leiste (immer vorhanden)
        self.status_label = tk.Label(self.root, text="", font=('Arial',10,'bold'),
                                     fg='white', bg='#1a252f')
        self.status_label.pack(fill='x', side='bottom', pady=(0,10))

        # Unsichtbare persistente Widgets erstellen
        self.create_persistent_widgets()

        # Hauptmenü anzeigen
        self.main_menu()

        # Verbindung und Serial-Thread
        self.connect_serial()
        threading.Thread(target=self.read_serial, daemon=True).start()



    def create_persistent_widgets(self):
        """Erstelle alle Widgets die persistent bleiben sollen"""
        self.dtc_label = tk.Label(self.root, text="–", font=('Digital-7',32),
                                  fg='#27ae60', bg='#2c3e50')
        self.rpm_value_label = tk.Label(self.root, text="0", font=('Digital-7',48),
                                        fg='#e74c3c', bg='#2c3e50')
        self.speed_label = tk.Label(self.root, text="0", font=('Digital-7',48),
                                    fg='#3498db', bg='#2c3e50')
        self.load_label = tk.Label(self.root, text="0", font=('Digital-7',48),
                                   fg='#f39c12', bg='#2c3e50')
        self.boost_label = tk.Label(self.root, text="0", font=('Digital-7',48),
                                    fg='#9b59b6', bg='#2c3e50')
        self.fuel_label = tk.Label(self.root, text="0", font=('Digital-7',48),
                                   fg='#2ecc71', bg='#2c3e50')
        self.batt_label = tk.Label(self.root, text="0.0", font=('Digital-7',48),
                                   fg='#f1c40f', bg='#2c3e50')

        # RPM-Canvas + Bar
        self.rpm_canvas = Canvas(self.root, width=500, height=90,
                                 bg='#2c3e50', highlightthickness=2, highlightbackground='#7f8c8d')
        bar_x, bar_y, bar_w, bar_h = 0, 20, 500, 20
        intervals = 7
        step = bar_w/intervals
        self.rpm_canvas.create_rectangle(bar_x-2, bar_y-2, bar_x+bar_w+2, bar_y+bar_h+2,
                                         fill='#1a252f', outline='#7f8c8d', width=2)
        self.rpm_bar = self.rpm_canvas.create_rectangle(bar_x, bar_y, bar_x, bar_y+bar_h,
                                                         fill='#27ae60', outline='')
        for i in range(intervals+1):
            x = bar_x + i*step
            self.rpm_canvas.create_line(x, bar_y-5, x, bar_y+bar_h+5, fill='white', width=1)
            self.rpm_canvas.create_text(x, bar_y+bar_h+15, text=str(i*1000),
                                        font=('Arial',9,'bold'), fill='#bdc3c7')

        # Liste aller persistenten Widgets für einfachere Verwaltung
        self.persistent_widgets = [
            self.status_label, self.dtc_label, self.rpm_value_label, 
            self.speed_label, self.load_label, self.boost_label,
            self.fuel_label, self.batt_label, self.rpm_canvas
        ]



    def hide_all_persistent_widgets(self):
        """Verstecken aller persistenten Widgets"""
        for widget in self.persistent_widgets:
            if widget != self.status_label:  # Status-Label bleibt sichtbar
                widget.pack_forget()



    def clear_current_view(self):
        """Löschen des aktuellen View-Frame, nicht die persistenten Widgets"""
        if self.current_view_frame:
            self.current_view_frame.destroy()
            self.current_view_frame = None
        self.hide_all_persistent_widgets()



    def main_menu(self):
        self.clear_current_view()
        self.current_view_frame = tk.Frame(self.root, bg='#2c3e50')
        self.current_view_frame.pack(expand=True, fill='both')
        
        tk.Label(self.current_view_frame, text="OBD2 Dashboard", font=('Arial',36,'bold'),
                 fg='white', bg='#2c3e50').pack(pady=50)
        btn_style = {'font':('Arial',24,'bold'),'width':10,'height':2,'relief':'flat'}
        tk.Button(self.current_view_frame, text="LIVE", command=self.live_view,
                  bg='#27ae60', fg='white', **btn_style).pack(side='left', padx=50)
        tk.Button(self.current_view_frame, text="ERROR", command=self.error_view,
                  bg='#e74c3c', fg='white', **btn_style).pack(side='right', padx=50)



    def live_view(self):
        self.clear_current_view()
        self.current_view_frame = tk.Frame(self.root, bg='#2c3e50')
        self.current_view_frame.pack(expand=True, fill='both', padx=15, pady=15)

        tk.Button(self.current_view_frame, text="Zurück", command=self.back_to_menu,
                  font=('Arial',12,'bold'), bg='#95a5a6', fg='white',
                  relief='flat', cursor='hand2').pack(anchor='nw')

        tk.Label(self.current_view_frame, text="DTC Count:", font=('Arial',12,'bold'),
                 fg='white', bg='#2c3e50').pack(anchor='w', pady=(20,0))
        self.dtc_label.config(bg='#2c3e50')
        self.dtc_label.pack(in_=self.current_view_frame, anchor='w', pady=(0,20))

        rpm_frame = tk.Frame(self.current_view_frame, bg='#2c3e50')
        rpm_frame.pack(fill='x', pady=(0,20))
        tk.Label(rpm_frame, text="RPM:", font=('Arial',12,'bold'),
                 fg='white', bg='#2c3e50').pack(side='left')
        self.rpm_value_label.pack(in_=rpm_frame, side='left', padx=(5,20))
        self.rpm_canvas.pack(in_=rpm_frame, side='left')

        for text, widget in [("Speed (km/h):", self.speed_label),
                             ("Load (%):", self.load_label),
                             ("Boost (kPa):", self.boost_label),
                             ("Fuel (%):", self.fuel_label),
                             ("Batt (V):", self.batt_label)]:
            tk.Label(self.current_view_frame, text=text, font=('Arial',12,'bold'),
                     fg='white', bg='#2c3e50').pack(anchor='w')
            widget.pack(in_=self.current_view_frame, anchor='w', pady=(0,20))

        self.status_label.config(text="Live-Modus", fg='#f39c12')



    def error_view(self):
        self.clear_current_view()
        self.current_view_frame = tk.Frame(self.root, bg='#2c3e50')
        self.current_view_frame.pack(expand=True, fill='both', padx=15, pady=15)

        tk.Button(self.current_view_frame, text="Zurück", command=self.back_to_menu,
                  font=('Arial',12,'bold'), bg='#95a5a6', fg='white',
                  relief='flat', cursor='hand2').pack(anchor='nw')

        dtc_frame = tk.LabelFrame(self.current_view_frame, text=" Fehlerdiagnose ",
                                  font=('Arial',12,'bold'), fg='#ecf0f1',
                                  bg='#34495e', labelanchor='n')
        dtc_frame.pack(fill='x', pady=(20,15))
        inner = tk.Frame(dtc_frame, bg='#34495e')
        inner.pack(fill='x', padx=15, pady=10)
        tk.Label(inner, text="Fehlercodes (DTCs):",
                 font=('Arial',11,'bold'), fg='#ecf0f1', bg='#34495e').pack(anchor='w')
        self.dtc_label.config(bg='#34495e', fg='#95a5a6')
        self.dtc_label.pack(in_=inner, anchor='w', pady=(5,0))

        btn_frame = tk.Frame(self.current_view_frame, bg='#2c3e50')
        btn_frame.pack(fill='x', pady=(20,0))
        tk.Button(btn_frame, text="Fehler löschen", command=self.clear_dtcs,
                  bg='#e74c3c', fg='white', font=('Arial',11,'bold'),
                  relief='flat', cursor='hand2').pack(side='left', padx=5)

        self.status_label.config(text="Error-Modus", fg='#f39c12')



    def back_to_menu(self):
        self.main_menu()



    def connect_serial(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
            time.sleep(2)
            self.status_label.config(text=f"Verbunden mit {SERIAL_PORT}", fg='#27ae60')
        except Exception as e:
            messagebox.showerror("Verbindungsfehler", str(e))
            self.status_label.config(text="Verbindungsfehler", fg='#e74c3c')



    def disconnect_serial(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.status_label.config(text="Verbindung getrennt", fg='#95a5a6')



    def clear_dtcs(self):
        if self.ser and self.ser.is_open:
            self.ser.write(b"CLEAR_DTC\n")
            self.status_label.config(text="DTC-Löschbefehl gesendet", fg='#f39c12')
        else:
            messagebox.showwarning("Warnung","Keine Verbindung!")



    def read_serial(self):
        while self.running:
            try:
                if self.ser and self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8',errors='ignore').strip()
                    print(f"Empfangen: {line}")  # Debug-Ausgabe
                    
                    if line.startswith("DTC_COUNT:"):
                        cnt = int(line.split(":")[1])
                        self.dtc_label.config(text=("Keine Fehler" if cnt==0 else f"{cnt} Fehler"),
                                              fg=('#27ae60' if cnt==0 else '#e74c3c'))
                    elif line.startswith("RPM:"):
                        rpm = int(line.split(":")[1])
                        self.rpm_value_label.config(text=f"{rpm} U/min")
                        self.draw_rpm_bar(rpm)
                    elif line.startswith("SPEED:"):
                        spd = int(line.split(":")[1])
                        self.speed_label.config(text=f"{spd} km/h")
                    elif line.startswith("LOAD:"):
                        ld = int(line.split(":")[1])
                        self.load_label.config(text=f"{ld} %")
                    elif line.startswith("BOOST:"):
                        b = int(line.split(":")[1])
                        self.boost_label.config(text=f"{b} kPa")
                    elif line.startswith("FUEL:"):
                        f = int(line.split(":")[1])
                        self.fuel_label.config(text=f"{f} %")
                    elif line.startswith("BATT:"):
                        batt = float(line.split(":")[1])
                        self.batt_label.config(text=f"{batt:.1f} V")
            except Exception as e:
                print(f"Serial read error: {e}")
                
            time.sleep(DATA_INTERVAL)



    def draw_rpm_bar(self, rpm):
        try:
            bar_x,bar_y,bar_w,bar_h = 0,20,500,20
            max_rpm = 7000
            w = int(min(rpm,max_rpm)/max_rpm*bar_w)
            color = '#27ae60' if rpm<3000 else '#f39c12' if rpm<5000 else '#e74c3c'
            self.rpm_canvas.coords(self.rpm_bar, bar_x,bar_y,bar_x+w,bar_y+bar_h)
            self.rpm_canvas.itemconfig(self.rpm_bar, fill=color)
        except Exception as e:
            print(f"RPM bar error: {e}")



    def on_close(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()



if __name__=="__main__":
    root = tk.Tk()
    app = OBDGui(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
