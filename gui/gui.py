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
import subprocess
import json
import os

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAIL Mass Spectrometry Analysis")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #800000;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: black;
            }
                        """)
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
        title.setStyleSheet("text-align: center; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        upload_button = QPushButton("Select mzML")
        upload_button.clicked.connect(self.load_file)
        layout.addWidget(upload_button)

        layout.addStretch()

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Data File", "", "mzML Files (*.mzML)")
        if not path:
            return
        
        # Stores the selected .mzML file path for later use
        self.controller.shared_data["file_path"] = path

        # Defines the Parser.py script location (absolute)
        parser_script = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Pipeline", "parser2.py"))

        # Tells where Parser.py will create the JSON file
        output_json = os.path.splitext(path)[0] + ".json"

        # Log for which file is being parsed
        print(f"Parsing file with parser.py: {path}")

        if not os.path.exists(parser_script):
            print(f"Parser script not found: {parser_script}")
            return

        # Run parser.py with the mzML path using the same Python executable
        try:
            completed = subprocess.run([sys.executable, parser_script, path], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running parser.py: {e}")
            return

        # Loads the generated JSON
        if os.path.exists(output_json):
            with open(output_json, "r", encoding="utf-8") as f:
                data = json.load(f)

            # ✅ store raw spectra data (arrays included)
            self.controller.shared_data["spectra_data"] = data  
            if not data:
                print("No spectra loaded from JSON.")
                return

            print(f"Parsed and loaded {len(data)} spectra from JSON")
            self.controller.show_page(self.controller.config_page)
        else:
            print("'parser.py' did not create a JSON file.")


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

        button_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(lambda: self.controller.show_page(self.controller.upload_page))
        button_layout.addWidget(back_btn)
        layout.addLayout(button_layout)

        layout.addStretch()

    def next_step(self):
        # Store chemical selection
        self.controller.shared_data["chemical"] = self.chemical_box.currentText()

        # Get paths
        mzml_path = self.controller.shared_data.get("file_path")
        json_path = os.path.splitext(mzml_path)[0] + ".json"

        # Path to Graph.py (absolute)
        graph_script = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Pipeline", "Graph.py"))

        print(f"Running Graph.py using {json_path}")

        if not os.path.exists(graph_script):
            print(f"Graph script not found: {graph_script}")
        else:
            try:
                completed = subprocess.run([sys.executable, graph_script, json_path, "--method", "round"], check=True, capture_output=True, text=True)
                if completed.stdout:
                    print("Graph.py stdout:", completed.stdout)
                if completed.stderr:
                    print("Graph.py stderr:", completed.stderr)
                print("Graph.py executed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error running Graph.py: {e}")
                print("stdout:", getattr(e, "stdout", None))
                print("stderr:", getattr(e, "stderr", None))
                return

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