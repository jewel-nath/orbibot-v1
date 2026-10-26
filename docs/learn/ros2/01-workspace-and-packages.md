# 01 - Workspace and Packages

**Setting up ROS2 development environment**

---

## 🎯 Learning Objectives

- Create a ROS2 workspace
- Understand package structure
- Build packages with colcon
- Source the environment

---

## 📁 What is a Workspace?

A **workspace** is a directory containing ROS2 packages.

```
ros2_ws/                    ← Workspace root
├── build/                  ← Build artifacts (auto-created)
├── install/                ← Installed packages (auto-created)
├── log/                    ← Build logs (auto-created)
└── src/                    ← Your packages go here
    ├── package_a/
    ├── package_b/
    └── orbibot_hardware/   ← OrbiBot packages
```

---

## 🛠️ Creating a Workspace

```bash
# Create directory
mkdir -p ~/ros2_ws/src

# Navigate to workspace
cd ~/ros2_ws

# Build (first time)
colcon build

# Source the environment
source install/setup.bash

# (Optional) Add to .bashrc to auto-source
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
```

---

## 📦 Package Structure

A ROS2 package has required files:

```
my_package/                 ← Package directory
├── package.xml             ← Package metadata
├── setup.py                ← Python package setup
├── resource/
│   └── my_package          ← Empty marker file
├── my_package/             ← Python code
│   ├── __init__.py
│   └── my_node.py
└── launch/                 ← Launch files
    └── my_launch.py
```

### package.xml

```xml
<?xml version="1.0"?>
<package format="3">
  <name>my_package</name>
  <version>0.0.1</version>
  <description>My awesome package</description>
  <maintainer email="me@example.com">My Name</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_python</buildtool_depend>
  
  <exec_depend>rclpy</exec_depend>
  <exec_depend>std_msgs</exec_depend>
</package>
```

### setup.py

```python
from setuptools import setup

package_name = 'my_package'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='My Name',
    maintainer_email='me@example.com',
    description='My awesome package',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'my_node = my_package.my_node:main',
        ],
    },
)
```

---

## 🔨 Building with Colcon

```bash
# Build all packages
colcon build

# Build specific package
colcon build --packages-select my_package

# Build with symlink (faster for Python)
colcon build --symlink-install

# Build specific package with symlink
colcon build --packages-select my_package --symlink-install

# Clean build (remove build/ install/ log/)
rm -rf build/ install/ log/
colcon build
```

### Why --symlink-install?

```
Without symlink:
  - Changes require rebuild
  - Slow iteration

With symlink:
  - Changes reflected immediately
  - Fast Python development
```

---

## 🔄 Sourcing the Environment

```bash
# After building, source to use packages
source install/setup.bash

# Check it worked
ros2 pkg list | grep my_package

# See package executables
ros2 pkg executables my_package
```

### Common Issue: "Package not found"

```bash
# Did you source?
source ~/ros2_ws/install/setup.bash

# Is ROS2 sourced?
source /opt/ros/jazzy/setup.bash

# Rebuild if needed
colcon build --packages-select my_package
source install/setup.bash
```

---

## 🎯 Key Takeaways

1. **Workspace** = Directory with src/, build/, install/, log/
2. **Package** = Directory with package.xml and setup.py
3. **colcon build** = Compiles and installs packages
4. **source install/setup.bash** = Makes packages available
5. **--symlink-install** = Faster Python development

---

## 📖 Next Steps

Learn about nodes:

**→ Continue to:** [02 - Nodes and Executors](02-nodes-and-executors.md)

---

*Last Updated: March 2026*