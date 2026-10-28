"use client";

import * as React from "react";
import {
  Tag,
  Plus,
  Upload,
  Search,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet,
  Layers,
  History,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { useToast } from "@/components/ui/Toast";
import { adminApi, FaultCatalogItem, FaultCatalogCreate, FaultCatalogUpdate } from "@/lib/api";

export default function AdminCatalogPage() {
  const { showToast } = useToast();

  const [items, setItems] = React.useState<FaultCatalogItem[]>([]);
  const [search, setSearch] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(true);

  // Create / Edit modal
  const [showItemModal, setShowItemModal] = React.useState(false);
  const [editingItem, setEditingItem] = React.useState<FaultCatalogItem | null>(null);
  const [faultCode, setFaultCode] = React.useState("");
  const [name, setName] = React.useState("");
  const [categoryId, setCategoryId] = React.useState("");
  const [laborMin, setLaborMin] = React.useState(30000);
  const [laborMax, setLaborMax] = React.useState(50000);
  const [partsMin, setPartsMin] = React.useState(0);
  const [partsMax, setPartsMax] = React.useState(0);
  const [safetyNotes, setSafetyNotes] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // CSV Import modal
  const [showCsvModal, setShowCsvModal] = React.useState(false);
  const [csvFile, setCsvFile] = React.useState<File | null>(null);
  const [isImporting, setIsImporting] = React.useState(false);

  const loadCatalog = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await adminApi.getFaultCatalog(search.trim() || undefined);
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setItems(data.items);
      if (data.items.length > 0 && !categoryId) {
        setCategoryId(data.items[0].category_id);
      }
    }
  }, [search, categoryId, showToast]);

  React.useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  const handleOpenCreate = () => {
    setEditingItem(null);
    setFaultCode("");
    setName("");
    setLaborMin(30000);
    setLaborMax(50000);
    setPartsMin(0);
    setPartsMax(0);
    setSafetyNotes("");
    setShowItemModal(true);
  };

  const handleOpenEdit = (item: FaultCatalogItem) => {
    setEditingItem(item);
    setFaultCode(item.fault_code);
    setName(item.name);
    setCategoryId(item.category_id);
    setLaborMin(item.labor_min);
    setLaborMax(item.labor_max);
    setPartsMin(item.parts_min);
    setPartsMax(item.parts_max);
    setSafetyNotes(item.safety_notes || "");
    setShowItemModal(true);
  };

  const handleSaveItem = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    if (editingItem) {
      // Update -> increments version
      const payload: FaultCatalogUpdate = {
        name,
        labor_min: Number(laborMin),
        labor_max: Number(laborMax),
        parts_min: Number(partsMin),
        parts_max: Number(partsMax),
        safety_notes: safetyNotes.trim() || undefined,
      };
      const { error } = await adminApi.updateFaultCatalog(editingItem.id, payload);
      setIsSubmitting(false);
      if (error) {
        showToast(error.message, "error");
        return;
      }
      showToast("Đã cập nhật mục lỗi và nâng phiên bản thành công (FR-ADM-02)!", "success");
    } else {
      // Create new -> version 1
      const payload: FaultCatalogCreate = {
        category_id: categoryId || "cat-default",
        fault_code: faultCode.trim().toUpperCase(),
        name,
        labor_min: Number(laborMin),
        labor_max: Number(laborMax),
        parts_min: Number(partsMin),
        parts_max: Number(partsMax),
        safety_notes: safetyNotes.trim() || undefined,
      };
      const { error } = await adminApi.createFaultCatalog(payload);
      setIsSubmitting(false);
      if (error) {
        showToast(error.message, "error");
        return;
      }
      showToast("Đã thêm lỗi mới vào bảng giá chuẩn!", "success");
    }

    setShowItemModal(false);
    loadCatalog();
  };

  const handleCsvImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;

    setIsImporting(true);
    const { data, error } = await adminApi.importFaultCatalogCsv(csvFile);
    setIsImporting(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast(data?.message || "Nhập file CSV thành công!", "success");
    setShowCsvModal(false);
    setCsvFile(null);
    loadCatalog();
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat("vi-VN").format(amount) + " đ";
  };

  return (
    <div className="space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-white">Bảng Giá Chuẩn & Phiên Bản</h2>
          <p className="text-xs text-slate-400">Quản lý mã lỗi, khoảng giá và versioning (FR-ADM-02)</p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="default"
            className="min-h-[40px] text-xs"
            onClick={() => setShowCsvModal(true)}
          >
            <Upload className="w-3.5 h-3.5 mr-1" />
            <span>Nhập CSV</span>
          </Button>

          <Button
            variant="primary"
            size="default"
            className="min-h-[40px] text-xs font-semibold"
            onClick={handleOpenCreate}
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            <span>Thêm Mới</span>
          </Button>
        </div>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tìm theo mã lỗi hoặc tên dịch vụ..."
          className="w-full bg-surface-card border border-surface-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
        />
      </div>

      {/* Catalog Items List */}
      {isLoading ? (
        <div className="py-16 text-center text-xs text-slate-400">Đang tải bảng giá lỗi...</div>
      ) : items.length === 0 ? (
        <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl text-xs text-slate-400">
          Chưa có mục lỗi nào phù hợp.
        </div>
      ) : (
        <div className="space-y-2.5">
          {items.map((it) => (
            <Card key={it.id} className="bg-surface-card border-surface-border">
              <CardContent className="p-3.5 space-y-2">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-brand-primary bg-brand-950/60 border border-brand-500/30 px-2 py-0.5 rounded-md">
                        {it.fault_code}
                      </span>
                      <span className="text-[10px] font-bold text-amber-300 bg-amber-950/60 border border-amber-500/40 px-1.5 py-0.5 rounded-md">
                        v{it.version}
                      </span>
                      <span className="text-xs text-slate-400">
                        {it.category_name || "Dịch vụ"}
                      </span>
                    </div>
                    <h3 className="font-bold text-white text-sm mt-1">{it.name}</h3>
                  </div>

                  <Button
                    variant="secondary"
                    size="default"
                    className="min-h-[36px] text-xs px-2.5"
                    onClick={() => handleOpenEdit(it)}
                  >
                    <Edit2 className="w-3 h-3 mr-1" />
                    <span>Sửa</span>
                  </Button>
                </div>

                {/* Price range breakdown */}
                <div className="grid grid-cols-2 gap-2 p-2 bg-surface-elevated rounded-xl text-xs border border-surface-border/50">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Tiền công chuẩn:</span>
                    <strong className="text-slate-200">
                      {formatVND(it.labor_min)} - {formatVND(it.labor_max)}
                    </strong>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Linh kiện / Phụ tùng:</span>
                    <strong className="text-emerald-400">
                      {it.parts_max > 0
                        ? `${formatVND(it.parts_min)} - ${formatVND(it.parts_max)}`
                        : "Không kèm phụ tùng"}
                    </strong>
                  </div>
                </div>

                {it.safety_notes && (
                  <p className="text-[11px] text-amber-400 italic">
                    Lưu ý an toàn: {it.safety_notes}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit BottomSheet */}
      <BottomSheet
        isOpen={showItemModal}
        onClose={() => setShowItemModal(false)}
        title={editingItem ? `Chỉnh Sửa Mã Lỗi #${editingItem.fault_code} (v${editingItem.version})` : "Thêm Mã Lỗi Mới"}
      >
        <form onSubmit={handleSaveItem} className="space-y-4">
          {!editingItem && (
            <Input
              label="Mã Lỗi (Fault Code) *"
              value={faultCode}
              onChange={(e) => setFaultCode(e.target.value)}
              placeholder="VD: MOTO_PUNC_01"
              required
            />
          )}

          <Input
            label="Tên sự cố / Dịch vụ sửa chữa *"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="VD: Vá xăm xe số lưu động"
            required
          />

          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Tiền công tối thiểu (VND) *"
              type="number"
              value={laborMin}
              onChange={(e) => setLaborMin(Number(e.target.value))}
              required
            />
            <Input
              label="Tiền công tối đa (VND) *"
              type="number"
              value={laborMax}
              onChange={(e) => setLaborMax(Number(e.target.value))}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Linh kiện tối thiểu (VND)"
              type="number"
              value={partsMin}
              onChange={(e) => setPartsMin(Number(e.target.value))}
            />
            <Input
              label="Linh kiện tối đa (VND)"
              type="number"
              value={partsMax}
              onChange={(e) => setPartsMax(Number(e.target.value))}
            />
          </div>

          <Input
            label="Lưu ý an toàn kỹ thuật (Tùy chọn)"
            value={safetyNotes}
            onChange={(e) => setSafetyNotes(e.target.value)}
            placeholder="VD: Đợi máy nguội trước khi kiểm tra bugi..."
          />

          <p className="text-[11px] text-slate-400">
            {editingItem
              ? "Cập nhật sẽ tự động tăng số phiên bản (version). Các đơn hàng cũ đã báo giá sẽ giữ nguyên giá trị tại thời điểm tạo."
              : "Mục mới sẽ được khởi tạo với phiên bản 1 (v1)."}
          </p>

          <Button type="submit" variant="primary" size="lg" className="w-full font-bold" isLoading={isSubmitting}>
            {editingItem ? "Lưu & Tăng Phiên Bản" : "Tạo Mã Lỗi Mới"}
          </Button>
        </form>
      </BottomSheet>

      {/* CSV Import BottomSheet */}
      <BottomSheet
        isOpen={showCsvModal}
        onClose={() => setShowCsvModal(false)}
        title="Nhập Bảng Giá Từ File CSV"
      >
        <form onSubmit={handleCsvImport} className="space-y-4">
          <p className="text-xs text-slate-300 leading-relaxed">
            Tải lên file CSV chứa danh mục lỗi. File cần có các cột: <code>fault_code</code>, <code>name</code>, <code>labor_min</code>, <code>labor_max</code>, <code>parts_min</code>, <code>parts_max</code>, <code>safety_notes</code>.
          </p>

          <input
            type="file"
            accept=".csv"
            onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
            className="w-full text-xs text-slate-300 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-brand-600 file:text-white hover:file:bg-brand-500"
            required
          />

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full font-bold"
            disabled={!csvFile}
            isLoading={isImporting}
          >
            Bắt Đầu Nhập Dữ Liệu CSV
          </Button>
        </form>
      </BottomSheet>
    </div>
  );
}

