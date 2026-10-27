cmake_minimum_required(VERSION 3.8)
project(ika_imu C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(ika_imu_node src/imu_node.cpp src/icm20948.c)
target_include_directories(ika_imu_node PRIVATE include)
target_link_libraries(ika_imu_node m)
ament_target_dependencies(ika_imu_node rclcpp sensor_msgs)

install(TARGETS ika_imu_node DESTINATION lib/${PROJECT_NAME})

ament_package()
