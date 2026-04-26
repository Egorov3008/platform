"""
Flow contract tests — testing data flow between dialogs and handlers.

These tests verify that:
1. Keyboard handlers correctly write data to dialog_data before switch_to()
2. Following getters correctly read data written by previous handlers
3. Contracts between windows are respected (dialog_data/start_data compatibility)
4. Double-source data patterns (dialog_data OR start_data) work correctly
"""
