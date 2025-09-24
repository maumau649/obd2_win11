import tkinter as tk

root = tk.Tk()
root.title("GUI Test Window")
root.geometry("300x200")

label = tk.Label(root, text="Wenn du das siehst, funktioniert Tkinter!", 
                font=('Arial', 12), fg='blue')
label.pack(pady=20)

button = tk.Button(root, text="OK - Schließen", command=root.quit,
                  bg='lightblue', font=('Arial', 10))
button.pack(pady=10)

print("GUI Test gestartet...")
root.mainloop()
print("GUI Test beendet.")