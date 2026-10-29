#include <gtest/gtest.h>
#include <SDL.h>
#include <chrono>
#include <memory>
#include <thread>
#include <vector>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joy.hpp>
#include "joy/joy.hpp"

TEST(CalibratedNode, CentersVirtualStickAndPreservesEndpoints)
{
  rclcpp::init(0, nullptr);
  ASSERT_EQ(SDL_Init(SDL_INIT_JOYSTICK), 0);
  const int id = SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER, 6, 17, 1);
  ASSERT_GE(id, 0);
  SDL_Joystick * device = SDL_JoystickOpen(id);
  ASSERT_NE(device, nullptr);
  const std::string name = SDL_JoystickNameForIndex(id);
  rclcpp::NodeOptions options;
  options.parameter_overrides({
    rclcpp::Parameter("device_name", name),
    rclcpp::Parameter("axis_centers", std::vector<double>{0.1, -0.1}),
    rclcpp::Parameter("autorepeat_rate", 50.0)});
  auto driver = std::make_shared<joy::Joy>(options);
  auto probe = std::make_shared<rclcpp::Node>("calibration_probe");
  std::vector<float> axes;
  auto subscription = probe->create_subscription<sensor_msgs::msg::Joy>(
    "joy", 10, [&axes](sensor_msgs::msg::Joy::SharedPtr msg) {axes = msg->axes;});
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(driver);
  executor.add_node(probe);
  auto sample = [&](int raw0, int raw1, float expected0, float expected1) {
      SDL_JoystickSetVirtualAxis(device, 0, static_cast<Sint16>(raw0));
      SDL_JoystickSetVirtualAxis(device, 1, static_cast<Sint16>(raw1));
      const auto until = std::chrono::steady_clock::now() + std::chrono::seconds(3);
      while (std::chrono::steady_clock::now() < until) {
        executor.spin_some();
        if (axes.size() == 8 && std::abs(axes[0] - expected0) < 0.001f &&
          std::abs(axes[1] - expected1) < 0.001f)
        {
          return true;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
      }
      return false;
    };
  EXPECT_TRUE(sample(3277, -3277, 0.0f, 0.0f));
  EXPECT_TRUE(sample(32767, -32768, -1.0f, 1.0f));
  EXPECT_TRUE(sample(-32768, 32767, 1.0f, -1.0f));
  EXPECT_TRUE(sample(3277, -3277, 0.0f, 0.0f));
  executor.remove_node(driver);
  executor.remove_node(probe);
  subscription.reset();
  probe.reset();
  SDL_JoystickClose(device);
  driver.reset();
  rclcpp::shutdown();
}

TEST(CalibratedNode, DuplicateNamesDoNotSelectAnArbitraryController)
{
  rclcpp::init(0, nullptr);
  ASSERT_EQ(SDL_Init(SDL_INIT_JOYSTICK), 0);
  const int first = SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER, 6, 17, 1);
  const int second = SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER, 6, 17, 1);
  ASSERT_GE(first, 0);
  ASSERT_GE(second, 0);
  const std::string name = SDL_JoystickNameForIndex(first);
  ASSERT_EQ(name, SDL_JoystickNameForIndex(second));
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("device_name", name)});
  auto driver = std::make_shared<joy::Joy>(options);
  auto probe = std::make_shared<rclcpp::Node>("ambiguous_device_probe");
  size_t count = 0;
  auto sub = probe->create_subscription<sensor_msgs::msg::Joy>(
    "joy", 10, [&count](sensor_msgs::msg::Joy::SharedPtr) {++count;});
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(driver);
  executor.add_node(probe);
  const auto until = std::chrono::steady_clock::now() + std::chrono::milliseconds(700);
  while (std::chrono::steady_clock::now() < until) {
    executor.spin_some();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  EXPECT_EQ(count, 0u);
  executor.remove_node(driver);
  executor.remove_node(probe);
  sub.reset();
  probe.reset();
  driver.reset();
  rclcpp::shutdown();
}
