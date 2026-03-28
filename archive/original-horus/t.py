import tkinter as tk
from tkinter import ttk, messagebox

# الثوابت
UNITS = {
    "بت": 1/8,
    "بايت": 1,
    "كيلوبايت": 1024,
    "ميجابايت": 1024**2,
    "جيجابايت": 1024**3,
    "تيرابايت": 1024**4
}

GATES = {
    "AND": lambda a, b: a and b,
    "OR": lambda a, b: a or b,
    "NOT": lambda a, b: not a
}

BASE_FORMATS = {2: "b", 8: "o", 10: "d", 16: "X"}

# تحويل وحدات البيانات
def convert_unit():
    try:
        value = float(entry_value.get())
        from_unit = combo_from.get()
        to_unit = combo_to.get()
        result = value * UNITS[from_unit] / UNITS[to_unit]
        label_result.config(text=f"النتيجة: {result:.4f} {to_unit}")
    except Exception:
        messagebox.showerror("خطأ", "يرجى إدخال قيمة صحيحة واختيار وحدات مناسبة.")

# عمليات البوابات المنطقية
def logic_operation():
    try:
        gate = combo_gate.get()
        a = bool(int(entry_a.get()))
        b = bool(int(entry_b.get())) if gate != "NOT" else None
        result = GATES[gate](a, b)
        label_logic_result.config(text=f"النتيجة: {int(result)}")
    except Exception:
        messagebox.showerror("خطأ", "يرجى إدخال 0 أو 1 فقط.")

# تحويل الأنظمة العددية
def convert_base():
    try:
        value = int(entry_decimal.get())
        base = int(combo_base.get())
        converted = format(value, BASE_FORMATS[base])
        label_base_result.config(text=f"النتيجة: {converted}")
    except Exception:
        messagebox.showerror("خطأ", "يرجى إدخال عدد صحيح واختيار نظام صالح.")

# واجهة المستخدم
root = tk.Tk()
root.title("محول رقمي شامل")

# قسم تحويل الوحدات
tk.Label(root, text="قيمة:").grid(row=0, column=0)
entry_value = tk.Entry(root)
entry_value.grid(row=0, column=1)
combo_from = ttk.Combobox(root, values=list(UNITS.keys()))
combo_from.grid(row=0, column=2)
combo_from.set("بايت")
combo_to = ttk.Combobox(root, values=list(UNITS.keys()))
combo_to.grid(row=0, column=3)
combo_to.set("كيلوبايت")
tk.Button(root, text="تحويل", command=convert_unit).grid(row=0, column=4)
label_result = tk.Label(root, text="النتيجة:")
label_result.grid(row=1, column=0, columnspan=5)

# قسم البوابات المنطقية
tk.Label(root, text="A:").grid(row=2, column=0)
entry_a = tk.Entry(root)
entry_a.grid(row=2, column=1)
tk.Label(root, text="B:").grid(row=2, column=2)
entry_b = tk.Entry(root)
entry_b.grid(row=2, column=3)
combo_gate = ttk.Combobox(root, values=list(GATES.keys()))
combo_gate.grid(row=2, column=4)
combo_gate.set("AND")
tk.Button(root, text="تنفيذ", command=logic_operation).grid(row=2, column=5)
label_logic_result = tk.Label(root, text="النتيجة:")
label_logic_result.grid(row=3, column=0, columnspan=6)

# قسم تحويل الأنظمة
tk.Label(root, text="عدد عشري:").grid(row=4, column=0)
entry_decimal = tk.Entry(root)
entry_decimal.grid(row=4, column=1)
combo_base = ttk.Combobox(root, values=list(BASE_FORMATS.keys()))
combo_base.grid(row=4, column=2)
combo_base.set(2)
tk.Button(root, text="تحويل", command=convert_base).grid(row=4, column=3)
label_base_result = tk.Label(root, text="النتيجة:")
label_base_result.grid(row=5, column=0, columnspan=4)

root.mainloop()