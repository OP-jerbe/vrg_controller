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
