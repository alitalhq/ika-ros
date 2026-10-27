// ika_imu: Gemstone O1 üzerindeki ICM-20948'i SPI ile okuyup imu/data_raw
// (sensor_msgs/Imu) yayınlar. Sürücü kütüphanesi (icm20948.c/.h) T3
// Foundation'ın resmi örnek kodudur.
//
// Yönelim hesaplanmaz (orientation_covariance[0] = -1). EKF yalnızca z
// açısal hızını kullanır; bu yüzden açılışta robot HAREKETSİZKEN jiroskop
// sapması ölçülüp çıkarılır. Sapma kalmazsa yaw zamanla kayar.

#include <chrono>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"

extern "C" {
#include "icm20948.h"
}

using namespace std::chrono_literals;

namespace
{
constexpr double kGravity = 9.80665;
constexpr double kDegToRad = M_PI / 180.0;
}  // namespace

class ImuNode : public rclcpp::Node
{
public:
  ImuNode()
  : Node("ika_imu_node")
  {
    const auto spi_device = declare_parameter<std::string>("spi_device", "/dev/spidev0.3");
    frame_id_ = declare_parameter<std::string>("frame_id", "imu_link");
    const double rate = declare_parameter<double>("rate", 100.0);
    const int calibration_samples = declare_parameter<int>("calibration_samples", 300);
    gyro_variance_ = declare_parameter<double>("gyro_variance", 0.0004);
    accel_variance_ = declare_parameter<double>("accel_variance", 0.04);

    static char tag[] = "icm20948";
    handle_ = icm20948_create(&data_, tag);
    if (handle_ == nullptr) {
      throw std::runtime_error("icm20948_create başarısız");
    }
    if (icm20948_spi_bus_init(handle_, spi_device.c_str()) != 0) {
      throw std::runtime_error("SPI açılamadı: " + spi_device);
    }
    // Küçük bir kara robot için 500 dps / 4 g, 2000 dps'e göre 4 kat çözünürlük.
    if (icm20948_configure(handle_, ACCE_FS_4G, GYRO_FS_500DPS) != 0) {
      throw std::runtime_error("ICM-20948 yapılandırılamadı (WHO_AM_I?)");
    }

    calibrate(calibration_samples);

    publisher_ = create_publisher<sensor_msgs::msg::Imu>("imu/data_raw", rclcpp::SensorDataQoS());
    timer_ = create_wall_timer(
      std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::duration<double>(1.0 / rate)),
      std::bind(&ImuNode::tick, this));

    RCLCPP_INFO(
      get_logger(), "%s @ %.0f Hz, jiroskop sapması [deg/s]: %.3f %.3f %.3f",
      spi_device.c_str(), rate, bias_[0], bias_[1], bias_[2]);
  }

  ~ImuNode() override
  {
    if (handle_ != nullptr) {
      icm20948_delete(handle_);
    }
  }

private:
  void calibrate(int samples)
  {
    if (samples <= 0) {
      return;
    }
    RCLCPP_INFO(get_logger(), "jiroskop kalibrasyonu: robotu %d örnek boyunca oynatmayın...", samples);
    double sum[3] = {0.0, 0.0, 0.0};
    int ok = 0;
    for (int i = 0; i < samples; ++i) {
      if (icm20948_get_gyro(handle_) == 0) {
        sum[0] += data_.gx;
        sum[1] += data_.gy;
        sum[2] += data_.gz;
        ++ok;
      }
      rclcpp::sleep_for(5ms);
    }
    if (ok < samples / 2) {
      throw std::runtime_error("kalibrasyon sırasında IMU okunamadı");
    }
    for (int i = 0; i < 3; ++i) {
      bias_[i] = sum[i] / ok;
    }
  }

  void tick()
  {
    if (icm20948_get_acce(handle_) != 0 || icm20948_get_gyro(handle_) != 0) {
      RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000, "IMU okuma hatası");
      return;
    }

    sensor_msgs::msg::Imu msg;
    msg.header.stamp = now();
    msg.header.frame_id = frame_id_;
    msg.orientation_covariance[0] = -1.0;

    msg.linear_acceleration.x = data_.ax * kGravity;
    msg.linear_acceleration.y = data_.ay * kGravity;
    msg.linear_acceleration.z = data_.az * kGravity;
    msg.angular_velocity.x = (data_.gx - bias_[0]) * kDegToRad;
    msg.angular_velocity.y = (data_.gy - bias_[1]) * kDegToRad;
    msg.angular_velocity.z = (data_.gz - bias_[2]) * kDegToRad;

    for (int i = 0; i < 3; ++i) {
      msg.linear_acceleration_covariance[i * 4] = accel_variance_;
      msg.angular_velocity_covariance[i * 4] = gyro_variance_;
    }
    publisher_->publish(msg);
  }

  icm20948_handle_t handle_ = nullptr;
  icm20948_data_t data_{};
  double bias_[3] = {0.0, 0.0, 0.0};
  double gyro_variance_;
  double accel_variance_;
  std::string frame_id_;
  rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  int code = 0;
  try {
    rclcpp::spin(std::make_shared<ImuNode>());
  } catch (const std::exception & e) {
    RCLCPP_FATAL(rclcpp::get_logger("ika_imu_node"), "%s", e.what());
    code = 1;
  }
  rclcpp::shutdown();
  return code;
}
