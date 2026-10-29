#include <gtest/gtest.h>
#include <limits>
#include "joy/axis_calibration.hpp"

TEST(AxisCalibration, ZeroCentersPreserveLegacyScaling)
{
  for (double raw : {-1.0, -0.7, -0.05, 0.0, 0.04, 0.3, 1.0}) {
    const double expected = std::abs(raw) <= 0.05 ? 0.0 :
      -std::copysign((std::abs(raw) - 0.05) / 0.95, raw);
    EXPECT_NEAR(joy::calibrate_axis(raw, 0.0, 0.05), expected, 1e-12);
  }
}
TEST(AxisCalibration, RemovesBiasWithoutLosingEitherEndpoint)
{
  for (double center : {-0.15, 0.1, 0.3}) {
    EXPECT_DOUBLE_EQ(joy::calibrate_axis(center, center, 0.05), 0.0);
    EXPECT_DOUBLE_EQ(joy::calibrate_axis(-1.0, center, 0.05), 1.0);
    EXPECT_DOUBLE_EQ(joy::calibrate_axis(1.0, center, 0.05), -1.0);
    EXPECT_DOUBLE_EQ(joy::calibrate_axis(center + 0.001, center, 0.05), 0.0);
    EXPECT_DOUBLE_EQ(joy::calibrate_axis(center - 0.001, center, 0.05), 0.0);
  }
}
TEST(AxisCalibration, RejectsInvalidCalibration)
{
  for (double c : {-1.0, 1.0, std::numeric_limits<double>::quiet_NaN()}) {
    EXPECT_THROW(joy::calibrate_axis(0.0, c, 0.05), std::invalid_argument);
  }
  for (double d : {-0.01, 1.0, std::numeric_limits<double>::infinity()}) {
    EXPECT_THROW(joy::calibrate_axis(0.0, 0.0, d), std::invalid_argument);
  }
}
