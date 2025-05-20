from skimage.metrics import structural_similarity as ssim
import cv2
import numpy as np
import os

class WeldInspector:
    def __init__(self, config):
        self.ref_config = config["Weld_Reference_ROIs"]
        self.use_gabor = config.get("Use_Gabor_Filter", False)
        self.results = []
        self.output_dir = "inspection_results"
        os.makedirs(self.output_dir, exist_ok=True)

    def apply_gabor(self, img):
        filters = []
        for theta in np.arange(0, np.pi, np.pi / 4):
            kern = cv2.getGaborKernel((21, 21), 4.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F)
            filters.append(kern)
        accum = np.zeros_like(img, dtype=np.float32)
        for kern in filters:
            fimg = cv2.filter2D(img, cv2.CV_8UC3, kern)
            accum = np.maximum(accum, fimg.astype(np.float32))
        return accum.astype(np.uint8)

    def align_to_reference(self, ref_img, test_img):
        orb = cv2.ORB_create(500)
        kp1, des1 = orb.detectAndCompute(ref_img, None)
        kp2, des2 = orb.detectAndCompute(test_img, None)

        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            print("Warning: Insufficient features. Skipping alignment.")
            return test_img

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)[:30]

        if len(matches) < 5:
            print("Warning: Too few good matches. Skipping alignment.")
            return test_img

        src_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)

        M, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts)
        if M is None:
            print("Warning: Transformation matrix could not be estimated.")
            return test_img

        aligned = cv2.warpAffine(test_img, M, (ref_img.shape[1], ref_img.shape[0]))
        return aligned

    def inspect(self, position, test_img_path):
        print(f"[Inspection] Starting weld inspection for position {position}")
        ref_data = self.ref_config.get(str(position))
        if not ref_data:
            print(f"[Inspection] No reference data found for position {position}")
            return

        roi = ref_data["roi"]
        ref_img_path = ref_data["reference_image"]

        test_img = cv2.imread(test_img_path, cv2.IMREAD_GRAYSCALE)
        ref_img = cv2.imread(ref_img_path, cv2.IMREAD_GRAYSCALE)

        if test_img is None or ref_img is None:
            print("[Inspection] Could not load test or reference image.")
            return

        # Align test image to reference
        aligned_test_img = self.align_to_reference(ref_img, test_img)

        x, y, w, h = roi
        height, width = aligned_test_img.shape[:2]
        x = min(x, width - 1)
        y = min(y, height - 1)
        w = min(w, width - x)
        h = min(h, height - y)

        test_crop = aligned_test_img[y:y+h, x:x+w]
        ref_crop = ref_img[y:y+h, x:x+w]

        if test_crop.shape != ref_crop.shape:
            test_crop = cv2.resize(test_crop, (ref_crop.shape[1], ref_crop.shape[0]))

        if self.use_gabor:
            test_crop = self.apply_gabor(test_crop)
            ref_crop = self.apply_gabor(ref_crop)

        score, diff = ssim(ref_crop, test_crop, full=True)
        diff = (diff * 255).astype(np.uint8)
        heatmap = cv2.applyColorMap(255 - diff, cv2.COLORMAP_JET)

        label = "OK" if score > 0.75 else "NG"
        mode = "Gabor" if self.use_gabor else "Raw"
        result_text = f"POS {position} : {label} (SSIM-{mode}: {score:.3f})"
        print("[Inspection]", result_text)

        ref_vis = cv2.cvtColor(ref_crop, cv2.COLOR_GRAY2BGR)
        test_vis = cv2.cvtColor(test_crop, cv2.COLOR_GRAY2BGR)
        combined = cv2.hconcat([ref_vis, test_vis, heatmap])

        color = (0, 255, 0) if label == "OK" else (0, 0, 255)
        cv2.putText(combined, result_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        filename = os.path.join(self.output_dir, f"scan_pos{position}_{label}_{mode}_SSIM{score:.3f}.jpg")
        cv2.imwrite(filename, combined)

        self.results.append((position, result_text, combined))

    def show_all_results(self):
        print("[Inspection] Robot returned home. Displaying all weld inspections...")
        for _, result_text, image in sorted(self.results):
            cv2.imshow("Weld Inspection", image)
            print(result_text)
            cv2.waitKey(1000)
        cv2.destroyAllWindows()
        self.results.clear()

