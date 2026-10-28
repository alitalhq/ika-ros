"""ika_base_node parametreleri: varsayılanlar ve YAML okuma yardımcıları.

Aynı tanımlar hem ROS node'u hem de ROS'suz çalışan hw_check aracı
tarafından kullanılır; böylece ikisi aynı hardware.yaml'ı okur.

Pin: "GPIO22" (Gemstone hat adı) veya "gpiochipN:line". PWM: "ecap0", "epwm1:1".
Boş string = kullanılmıyor.
DİKKAT (ROS 2): float parametrelere YAML'da ondalıklı değer yazın (1 değil 1.0).
"""

DEFAULTS = {
    'backend': 'gpiod',               # gpiod | mock (donanımsız benzetim)
    'motor_driver': 'in_in_pwm',      # in_in_pwm (L298N/TB6612) | dir_pwm
    'brake_on_stop': False,
    'pwm_period_ns': 1_000_000,

    'left.in1': '', 'left.in2': '', 'left.pwm': '', 'left.invert': False,
    'right.in1': '', 'right.in2': '', 'right.pwm': '', 'right.invert': False,

    'encoder.mode': 'x4',             # x4 | x2 | none
    'encoder.bias': 'as-is',          # as-is | pull-up | pull-down | disabled
    'encoder.ppr': 0.0,               # A kanalı darbe / TEKER (çıkış mili) turu
    'left.enc_a': '', 'left.enc_b': '', 'left.enc_invert': False,
    'right.enc_a': '', 'right.enc_b': '', 'right.enc_invert': False,

    'wheel_radius': 0.0425,           # launch robot.yaml'dan geçirir
    'wheel_separation': 0.17,
    'max_wheel_speed': 0.5,           # %100 duty'deki teker hızı [m/s]
    'max_accel': 0.6,                 # [m/s^2]
    'control_rate': 50.0,
    'state_rate': 10.0,          # /joint_states ve ~/wheels (yalnızca görselleştirme/ayar)
    'cmd_timeout': 0.5,
    'speed_filter_alpha': 0.5,

    'pid.kp': 60.0,                   # [duty % / (m/s)]
    'pid.ki': 300.0,
    'pid.kff': 1.0,
    'pid.min_duty': 0.0,
    'pid.max_duty': 100.0,
    'pid.i_limit': 30.0,              # integralin duty katkısı üst sınırı [%]

    'odom_frame': 'odom',
    'base_frame': 'base_link',
    'publish_tf': False,
}


def flatten(tree: dict, prefix: str = '') -> dict:
    flat = {}
    for key, value in tree.items():
        name = f'{prefix}{key}'
        if isinstance(value, dict):
            flat.update(flatten(value, name + '.'))
        else:
            flat[name] = value
    return flat


def load_yaml_params(path: str, node_name: str = 'ika_base_node') -> dict:
    """ROS parametre YAML'ından bu node'un ayarlarını düz sözlük olarak döner."""
    import yaml
    with open(path) as f:
        doc = yaml.safe_load(f) or {}
    section = doc.get(node_name, doc.get(f'/{node_name}', {}))
    cfg = dict(DEFAULTS)
    cfg.update(flatten(section.get('ros__parameters', {})))
    return cfg
