# Must have ttkbootstrap installed
# pip install ttkbootstrap

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# A frame is like a view. Must handle navigation manualy
class App(ttk.Window):
    def __init__(self):
        super().__init__(title="CAIL Mass Spectrometry Analysis", themename="darkly", size=(900, 650))

        # Parent containter to hold views
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        # Global state 
        self.shared_data = {"file_path": None, "chemical": None, "dataframe": None}

        self.frames = {}
        for F in (UploadPage, ConfigPage, GraphPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(UploadPage)

    def show_frame(self, page):
        self.frames[page].tkraise()

class UploadPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Step 1: Upload Data File", font=("Helvetica", 20)).pack(pady=30)
        ttk.Button(self, text="Select CSV", bootstyle="primary", command=lambda: self.load_file(controller)).pack(pady=20)

    def load_file(self, controller):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if path:
            controller.shared_data["file_path"] = path
            df = pd.read_csv(path)
            controller.shared_data["dataframe"] = df
            controller.show_frame(ConfigPage)

class ConfigPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Step 2: Configuration", font=("Helvetica", 20)).pack(pady=30)
        ttk.Label(self, text="Select Chemical:", bootstyle="info").pack(pady=10)

        self.chemical_var = ttk.StringVar(value="CH2")
        chemicals = ["CH2", "H2O", "CO2", "NH3"]
        menu = ttk.OptionMenu(self, self.chemical_var, *chemicals)
        menu.pack(pady=10)

        ttk.Button(self, text="Continue →", bootstyle="success",
                   command=lambda: self.next_step(controller)).pack(pady=30)

    def next_step(self, controller):
        controller.shared_data["chemical"] = self.chemical_var.get()
        controller.show_frame(GraphPage)

class GraphPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Step 3: Graphs", font=("Helvetica", 20)).pack(pady=20)

        # Create figure
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True)

        # Action buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Save Graph", bootstyle="info", command=self.save_graph).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Export CSV", bootstyle="success", command=self.export_csv).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Toggle Noise Lines", bootstyle="warning", command=self.toggle_noise).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="← Back", bootstyle="secondary", command=lambda: controller.show_frame(ConfigPage)).pack(side=LEFT, padx=5)

        self.noise_enabled = False
        self.controller = controller

    def update_graph(self):
        df = self.controller.shared_data.get("dataframe")
        if df is not None:
            self.ax.clear()
            for col in df.columns[1:]:
                self.ax.plot(df[df.columns[0]], df[col], marker='.', label=col)
            self.ax.legend()
            self.ax.set_title(f"Graph for {self.controller.shared_data.get('chemical')}")
            self.canvas.draw()

    def save_graph(self):
        self.figure.savefig("output_graph.png")
        ttk.toast.show_toast("Graph saved!", title="Success")

    def export_csv(self):
        df = self.controller.shared_data.get("dataframe")
        if df is not None:
            df.to_csv("exported_data.csv", index=False)
            ttk.toast.show_toast("CSV exported!", title="Success")

    def toggle_noise(self):
        self.noise_enabled = not self.noise_enabled
        ttk.toast.show_toast(f"Noise {'enabled' if self.noise_enabled else 'disabled'}", title="Info")

if __name__ == "__main__":
    app = App()
    app.mainloop()