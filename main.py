import gmsh
import os


def analyze_cad_step(step_file, output_dir="results"):
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 初始化Gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)  # 启用控制台输出

    # 创建新模型
    gmsh.model.add("cad_analysis")

    # 1. 导入STEP文件
    print(f"Importing CAD file: {step_file}")
    gmsh.merge(step_file)

    # 可选：修复几何(如果导入有问题)
    gmsh.model.occ.healShapes()
    gmsh.model.occ.synchronize()

    # 2. 检查导入的实体
    entities = gmsh.model.getEntities()
    print("Imported entities:")
    for dim, tag in entities:
        print(f" - Dimension {dim}, tag {tag}")

    # 3. 定义物理组(需要根据您的模型调整)
    # 假设我们想分析所有3D体
    volumes = gmsh.model.getEntities(dim=3)
    if volumes:
        print("Found 3D volumes, creating physical group...")
        volume_tags = [v[1] for v in volumes]
        gmsh.model.addPhysicalGroup(3, volume_tags, 1)

        # 自动检测外表面用于边界条件
        surfaces = gmsh.model.getBoundary(volumes, oriented=False)
        gmsh.model.addPhysicalGroup(2, [s[1] for s in surfaces], 2)
    else:
        # 如果没有3D体，尝试处理2D面
        surfaces = gmsh.model.getEntities(dim=2)
        if surfaces:
            print("Found 2D surfaces, creating physical group...")
            gmsh.model.addPhysicalGroup(2, [s[1] for s in surfaces], 1)

            # 自动检测边界边
            curves = gmsh.model.getBoundary(surfaces, oriented=False)
            gmsh.model.addPhysicalGroup(1, [c[1] for c in curves], 2)

    # 4. 设置网格参数
    gmsh.option.setNumber("Mesh.Algorithm", 6)  # 6=Frontal
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)  # 1=Delaunay
    gmsh.option.setNumber("Mesh.Optimize", 1)
    gmsh.option.setNumber("Mesh.QualityType", 2)  # 2=Gamma quality measure

    # 设置全局网格大小(根据模型尺寸调整)
    gmsh.option.setNumber("Mesh.MeshSizeMin", 1.0)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 5.0)

    # 5. 生成网格
    print("Generating mesh...")
    gmsh.model.mesh.generate(3)  # 3D网格
    gmsh.model.mesh.optimize("Netgen")

    # 6. 保存网格文件
    mesh_file = os.path.join(output_dir, "cad_mesh.inp")
    gmsh.write(mesh_file)
    print(f"Mesh saved to {mesh_file}")

    # 7. 创建CalculiX输入文件
    ccx_input = os.path.join(output_dir, "analysis.inp")
    with open(ccx_input, "w") as f:
        f.write(f"""*HEADING
Stress analysis of imported CAD model
*INCLUDE, INPUT={os.path.basename(mesh_file)}
*MATERIAL, NAME=STEEL
*ELASTIC
210000, 0.3  # 钢的材料属性(弹性模量210GPa,泊松比0.3)
*SOLID SECTION, MATERIAL=STEEL, ELSET=1
*BOUNDARY
2, 1, 3, 0.0  # 固定所有外表面(根据实际情况调整)
*STEP
*STATIC
*DLOAD
1, P, 10  # 施加压力(根据实际情况调整)
*NODE PRINT, NSET=NALL
U
*EL PRINT, ELSET=EALL
S
*END STEP
""")

    # 8. 关闭Gmsh
    gmsh.finalize()

    # 9. 运行CalculiX求解器
    print("Running CalculiX analysis...")
    os.chdir(output_dir)
    os.system("ccx analysis -o vtk")

    # 10. 返回结果文件路径
    result_file = os.path.join(output_dir, "analysis.vtk")
    print(f"Analysis completed. Results saved to {result_file}")
    return result_file


if __name__ == "__main__":
    step_file = "test_cube.step"  # 替换为您的STEP文件路径
    result = analyze_cad_step(step_file)