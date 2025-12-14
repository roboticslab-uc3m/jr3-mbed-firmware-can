cmake_minimum_required(VERSION 3.19)
cmake_policy(VERSION 3.19...3.22)

set(MBED_APP_JSON_PATH mbed_app.json5)

include(mbed-os/tools/cmake/mbed_toolchain_setup.cmake)

project(jr3-mbed-firmware-can
        LANGUAGES C CXX ASM)

include(mbed_project_setup)

add_subdirectory(mbed-os)
add_subdirectory(jr3)

add_executable(${PROJECT_NAME} main.cpp Motor/Motor.h Motor/Motor.cpp)
target_link_libraries(${PROJECT_NAME} mbed-os jr3)
mbed_set_post_build(${PROJECT_NAME})
