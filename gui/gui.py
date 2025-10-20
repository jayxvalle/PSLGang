# Must have PyQt6 and matplotlib installed
# pip install PyQt6 matplotlib pandas

import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QStackedWidget, QComboBox, QHBoxLayout
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAIL Mass Spectrometry Analysis")
        self.resize(900, 650)

        # Shared global state
        self.shared_data = {"file_path": None, "chemical": None, "dataframe": None}

        # Main layout manager (stack of pages)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Initialize pages
        self.upload_page = UploadPage(self)
        self.config_page = ConfigPage(self)
        self.graph_page = GraphPage(self)

        # Add pages to stack
        self.stack.addWidget(self.upload_page)
        self.stack.addWidget(self.config_page)
        self.stack.addWidget(self.graph_page)

        # Start at upload page
        self.show_page(self.upload_page)

    def show_page(self, page_widget):
        """Switches to the given page."""
        self.stack.setCurrentWidget(page_widget)


# Step 1: Upload Page
class UploadPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Step 1: Upload Data File")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        upload_button = QPushButton("Select CSV")
        upload_button.clicked.connect(self.load_file)
        layout.addWidget(upload_button)

        layout.addStretch()

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Data File", "", "CSV Files (*.csv)")
        if path:
            self.controller.shared_data["file_path"] = path
            df = pd.read_csv(path)
            self.controller.shared_data["dataframe"] = df
            self.controller.show_page(self.controller.config_page)


# Step 2: Config Page
class ConfigPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Step 2: Configuration")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        sub_label = QLabel("Select Chemical:")
        layout.addWidget(sub_label)

        self.chemical_box = QComboBox()
        self.chemical_box.addItems(["CH2", "H2O", "CO2", "NH3"])
        layout.addWidget(self.chemical_box)

        continue_btn = QPushButton("Continue →")
        continue_btn.clicked.connect(self.next_step)
        layout.addWidget(continue_btn)

        layout.addStretch()

    def next_step(self):
        self.controller.shared_data["chemical"] = self.chemical_box.currentText()
        self.controller.graph_page.update_graph()
        self.controller.show_page(self.controller.graph_page)


# Step 3: Graph Page
class GraphPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.noise_enabled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Step 3: Graphs")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Matplotlib figure
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Buttons
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        save_btn = QPushButton("💾 Save Graph")
        save_btn.clicked.connect(self.save_graph)
        button_layout.addWidget(save_btn)

        export_btn = QPushButton("📤 Export CSV")
        export_btn.clicked.connect(self.export_csv)
        button_layout.addWidget(export_btn)

        noise_btn = QPushButton("🧪 Toggle Noise Lines")
        noise_btn.clicked.connect(self.toggle_noise)
        button_layout.addWidget(noise_btn)

        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(lambda: self.controller.show_page(self.controller.config_page))
        button_layout.addWidget(back_btn)

    def update_graph(self):
        df = self.controller.shared_data.get("dataframe")
        chemical = self.controller.shared_data.get("chemical")

        if df is not None:
            self.ax.clear()
            for col in df.columns[1:]:
                self.ax.plot(df[df.columns[0]], df[col], marker='.', label=col)
            self.ax.legend()
            self.ax.set_title(f"Graph for {chemical}")
            self.canvas.draw()

    def save_graph(self):
        self.figure.savefig("output_graph.png")
        print("✅ Graph saved as output_graph.png")

    def export_csv(self):
        df = self.controller.shared_data.get("dataframe")
        if df is not None:
            df.to_csv("exported_data.csv", index=False)
            print("✅ CSV exported as exported_data.csv")

    def toggle_noise(self):
        self.noise_enabled = not self.noise_enabled
        print(f"Noise {'enabled' if self.noise_enabled else 'disabled'}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())