import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from PyQt6.QtCore import QObject, pyqtSignal

class ColorExtractor(QObject):
    finished = pyqtSignal(list, str) # result_list, error_msg
    log = pyqtSignal(str)

    def extract(self, image_path, n_colors=8):
        try:
            self.log.emit(f"正在加载图片: {image_path}")
            img = Image.open(image_path)
            
            # 缩放以加快计算
            img = img.resize((100, 100))
            
            # 转换为 numpy 数组 (只取 RGB，忽略 Alpha)
            img = img.convert('RGB')
            img_array = np.array(img)
            data = img_array.reshape(-1, 3)

            self.log.emit(f"正在进行 K-Means 聚类 ({n_colors} 色)...")
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
            kmeans.fit(data)

            # 获取中心点和标签
            colors = kmeans.cluster_centers_
            labels = kmeans.labels_
            
            # 计算占比
            counts = np.bincount(labels)
            proportions = counts / counts.sum()

            # 排序（按占比降序）
            sorted_indices = np.argsort(proportions)[::-1]
            
            results = []
            for i in sorted_indices:
                r, g, b = colors[i]
                prop = proportions[i]
                hex_code = "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))
                results.append({
                    'rgb': (int(r), int(g), int(b)),
                    'hex': hex_code,
                    'proportion': float(prop)
                })

            self.log.emit("提取完成")
            self.finished.emit(results, "")

        except Exception as e:
            self.log.emit(f"错误: {str(e)}")
            self.finished.emit([], str(e))
