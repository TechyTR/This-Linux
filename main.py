from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
import os
import platform

BOOT_LINES = [
    "[    0.000000] Linux version 6.1.0-fake (gcc)",
    "[    0.012345] Kernel command line: root=/dev/fake ro",
    "[    0.034521] CPU: ARM64 Processor detected",
    "[    0.056789] Memory: 4096MB available",
    "[    0.089012] Initializing cgroup subsys",
    "[    0.123456] SELinux: Initializing.",
    "[    0.145623] Mounting root filesystem...",
    "[    0.178901] su: binary patched successfully",
    "[    0.201234] Root access granted: uid=0(root)",
    "[    0.234567] Starting init process...",
    "[    0.267890] System boot complete.",
]


def get_storage_info():
    try:
        st = os.statvfs('/storage/emulated/0')
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        return used / (1024 ** 3), total / (1024 ** 3)
    except Exception:
        return None, None


def get_ram_info():
    try:
        meminfo = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().split()[0]
                    meminfo[key] = int(value)
        total_kb = meminfo.get('MemTotal', 0)
        avail_kb = meminfo.get('MemAvailable', 0)
        used_kb = total_kb - avail_kb
        return used_kb / (1024 ** 2), total_kb / (1024 ** 2)
    except Exception:
        return None, None


def get_device_model():
    try:
        from jnius import autoclass
        Build = autoclass('android.os.Build')
        return f"{Build.MANUFACTURER} {Build.MODEL}"
    except Exception:
        return platform.machine()


def get_battery_info():
    percentage = None
    is_charging = None
    watt = None
    try:
        from plyer import battery
        status = battery.status
        percentage = status.get('percentage')
        is_charging = status.get('isCharging')
    except Exception:
        pass

    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        BatteryManager = autoclass('android.os.BatteryManager')
        context = PythonActivity.mActivity
        bm = context.getSystemService('batterymanager')
        current_micro = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_NOW)
        voltage_micro = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_VOLTAGE)
        if current_micro and voltage_micro:
            amps = abs(current_micro) / 1_000_000
            volts = voltage_micro / 1_000_000
            watt = round(amps * volts, 2)
    except Exception:
        pass

    return percentage, is_charging, watt


class BootScreen(Screen):
    def on_enter(self):
        Window.clearcolor = (0, 0, 0, 1)
        layout = BoxLayout(orientation='vertical', padding=10)
        self.log_label = Label(
            text="", markup=True,
            color=(0, 1, 0, 1),
            halign='left', valign='top',
            text_size=(Window.width - 20, None)
        )
        layout.add_widget(self.log_label)
        self.add_widget(layout)

        self.lines_to_show = BOOT_LINES.copy()
        self.shown = []
        Clock.schedule_interval(self.add_line, 0.25)

    def add_line(self, dt):
        if self.lines_to_show:
            self.shown.append(self.lines_to_show.pop(0))
            self.log_label.text = "\n".join(self.shown)
        else:
            Clock.schedule_once(self.go_to_panel, 0.8)
            return False

    def go_to_panel(self, dt):
        self.manager.current = "panel"


class PanelScreen(Screen):
    def on_enter(self):
        Window.clearcolor = (0.05, 0.05, 0.05, 1)
        self.clear_widgets()

        root = BoxLayout(orientation='vertical', padding=20, spacing=15)
        root.add_widget(Label(text="[b]Kernel Panel[/b]", markup=True,
                               font_size=28, size_hint_y=None, height=50))

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        grid.add_widget(self.info_row("Cihaz Modeli", get_device_model()))

        used_ram, total_ram = get_ram_info()
        grid.add_widget(self.info_row(
            "RAM",
            f"{used_ram:.2f} GB / {total_ram:.2f} GB" if total_ram else "Alınamadı"
        ))

        used_st, total_st = get_storage_info()
        grid.add_widget(self.info_row(
            "Depolama",
            f"{used_st:.2f} GB / {total_st:.2f} GB" if total_st else "Alınamadı"
        ))

        percentage, is_charging, watt = get_battery_info()
        grid.add_widget(self.info_row(
            "Pil Yüzdesi", f"%{percentage}" if percentage is not None else "Alınamadı"
        ))
        grid.add_widget(self.info_row(
            "Şarj Durumu",
            "Şarj oluyor" if is_charging else ("Şarj olmuyor" if is_charging is not None else "Alınamadı")
        ))
        grid.add_widget(self.info_row(
            "Şarj Hızı", f"{watt} W" if watt else "Desteklenmiyor"
        ))

        scroll.add_widget(grid)
        root.add_widget(scroll)
        self.add_widget(root)

    def info_row(self, title, value):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        row.add_widget(Label(text=f"[b]{title}[/b]", markup=True, color=(0, 1, 0, 1)))
        row.add_widget(Label(text=str(value), color=(1, 1, 1, 1)))
        return row


class FakeKernelApp(App):
    def build(self):
        self.title = "Kernel Manager"
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(BootScreen(name="boot"))
        sm.add_widget(PanelScreen(name="panel"))
        return sm


if __name__ == "__main__":
    FakeKernelApp().run()
