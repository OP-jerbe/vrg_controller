from typing import LiteralString


def setting_label_style() -> LiteralString:
    return """
        QLabel {
            font-size: 20px;
        }
        """


def display_label_style() -> LiteralString:
    return """
        QLabel {
            font-size: 30px;            /* Large font */
            color: red;                 /* Red text */
            background-color: black;    /* Black background */
            border: 2px solid gray;     /* Gray border */
            border-style: outset;       /* Raised effect */
            padding: 5px;               /* Padding inside the label */
        }
        """


def line_edit_style() -> LiteralString:
    return """
        QLineEdit {
            font-size: 15px;
            color: #8bc34a;
        }
        QLineEdit:focus {
            color: #88ff00;
        }
        """


def warning_btn_style() -> LiteralString:
    """
    Set the color of the text in the Enable RF button to be yellow when there is a
    warning such as `HiT`.
    """
    return """
        QPushButton {
            color: #f9ff47
        }
    """


def default_btn_style() -> LiteralString:
    """
    Set the color of th text in the Enable RF button to the default green when
    everything is OK.
    """
    return """
        QPushButton {
            color: #8bc34a
        }
    """
