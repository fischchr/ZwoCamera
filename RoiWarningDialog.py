from PyQt5.QtWidgets import QDialog
from PyQt5.uic import loadUi
from PyQt5 import QtCore as qtc

class RoiWarningDialog(QDialog):
    def __init__(self, roi_h: int):
        # Call constructor of parent object
        super(RoiWarningDialog, self).__init__(flags=qtc.Qt.WindowStaysOnTopHint)

        # Load GUI
        loadUi('qt-gui/roi_warning_dialog.ui', self) 
        
        # Set title
        self.setWindowTitle('Warning: Large ROI')

        # Set warning text
        text = f'Recording might be slow due to large ROI height ({roi_h}). \nDo you want to continue?'
        self.WarningLabel.setText(text)

        # Connect signals
        self.ContinueButton.clicked.connect(self.accept)
        self.CancelButton.clicked.connect(self.reject)

    
    def dismiss_state(self):
        return self.IgnoreInput.isChecked()






