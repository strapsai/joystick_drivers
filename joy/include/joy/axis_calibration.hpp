#ifndef JOY__AXIS_CALIBRATION_HPP_
#define JOY__AXIS_CALIBRATION_HPP_

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace joy
{
// Centers are normalized SDL coordinates, before ROS sign inversion/deadzone.
inline double calibrate_axis(double raw, double center, double deadzone)
{
  if (!std::isfinite(center) || std::abs(center) >= 1.0 ||
    !std::isfinite(deadzone) || deadzone < 0.0 || deadzone >= 1.0)
  {
    throw std::invalid_argument("axis center must be finite in (-1,1); deadzone in [0,1)");
  }
  raw = std::max(-1.0, std::min(1.0, raw));
  const double corrected = (raw - center) / (raw >= center ? 1.0 - center : 1.0 + center);
  if (std::abs(corrected) <= deadzone) {
    return 0.0;
  }
  const double magnitude = (std::abs(corrected) - deadzone) / (1.0 - deadzone);
  return -std::copysign(magnitude, corrected);
}
}  // namespace joy
#endif  // JOY__AXIS_CALIBRATION_HPP_
