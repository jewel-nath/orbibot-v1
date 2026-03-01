# 02 - Xacro Macros

**Making URDF reusable and maintainable**

---

## 🎯 Learning Objectives

- Create Xacro macros
- Use parameters in macros
- Include other Xacro files

---

## 📝 Basic Macro

```xml
<xacro:macro name="wheel" params="name x y">
  <link name="${name}">
    <visual>
      <geometry>
        <cylinder radius="0.05" length="0.04"/>
      </geometry>
    </visual>
  </link>
  
  <joint name="${name}_joint" type="continuous">
    <parent link="base_link"/>
    <child link="${name}"/>
    <origin xyz="${x} ${y} 0"/>
    <axis xyz="0 1 0"/>
  </joint>
</xacro:macro>
```

### Using the Macro

```xml
<xacro:wheel name="wheel_fl" x="0.13" y="0.18"/>
<xacro:wheel name="wheel_fr" x="0.13" y="-0.18"/>
<xacro:wheel name="wheel_bl" x="-0.13" y="0.18"/>
<xacro:wheel name="wheel_br" x="-0.13" y="-0.18"/>
```

---

## 📦 Including Files

```xml
<?xml version="1.0"?>
<robot name="orbibot" xmlns:xacro="http://www.ros.org/wiki/xacro">

  <!-- Include other xacro files -->
  <xacro:include filename="materials.xacro"/>
  <xacro:include filename="wheels.xacro"/>
  <xacro:include filename="sensors.xacro"/>
  
  <!-- Build robot -->
  <xacro:base/>
  <xacro:all_wheels/>
  <xacro:sensors/>

</robot>
```

---

## 🎯 Key Takeaways

1. **Macros** = Reusable components
2. **Parameters** = Make macros flexible
3. **Include** = Split large files
4. **${}** = Variable substitution

---

## 📖 Next Steps

See OrbiBot's complete URDF:

**→ Continue to:** [03-orbibot-urdf-walkthrough.md](03-orbibot-urdf-walkthrough.md)

---

*Last Updated: March 2026*