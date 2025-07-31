 import {
  Badge,
  Box,
  Container,
  Flex,
  Heading,
  HStack,
  Image,
  Input,
  VStack,
  Button,
  Spinner,
  Text,
  EmptyState,
} from "@chakra-ui/react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { FiSearch, FiUpload, FiFile, FiX } from "react-icons/fi"
import { useState, useEffect, useRef, useCallback } from "react"

// Import API client
import { OcrService, type OCRRecordPublic, OpenAPI } from "../../client"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog"


// 临时类型定义，扩展OCRRecordPublic以包含运单字段
interface ExtendedOCRRecord extends OCRRecordPublic {
  waybill_number?: string
  carrier?: string
  shipping_date?: string
  recipient?: string
  delivery_date?: string
  upload_date?: string
  uploader?: string
  audit_status?: string
}

// 临时toast hook
const useCustomToast = () => ({
  showSuccessToast: (message: string) => {
    console.log('Success:', message)
    // 不使用alert，只在控制台输出消息
  },
  showErrorToast: (message: string) => {
    console.log('Error:', message)
    alert('错误: ' + message) // 保留错误提示的alert
  }
})


const PER_PAGE = 10

export const Route = createFileRoute("/_layout/waybills" as any)({
  component: Waybills,
  // 移除validateSearch以避免URL参数
})

// Mock data for development - 运单数据
const mockWaybillData = {
  data: [
    {
      id: "1",
      device_sn: "DEV001",
      waybill_number: "77301475051865１",
      carrier: "XXX物流",
      shipping_date: "2015-10-02T08:50:08",
      recipient: "li si",
      delivery_date: "2015-10-04T10:15:45",
      upload_date: "2015-10-02T09:30:15",
      uploader: "san zhang",
      audit_status: "未审核",
      original_image_url: "https://via.placeholder.com/300x200?text=Waybill",
      result_image_url: "https://via.placeholder.com/300x200?text=Result",
      ocr_text: "运单识别文本内容",
      ocr_confidence: 0.95,
      scan_time: "2015-10-02T09:30:15",
      status: "success",
    },
    {
      id: "2",
      device_sn: "DEV002", 
      waybill_number: "77301475051865２",
      carrier: "YYY快递",
      shipping_date: "2015-10-03T14:20:30",
      recipient: "wang wu",
      delivery_date: null,
      upload_date: "2015-10-03T15:00:00",
      uploader: "zhao liu",
      audit_status: "已审核",
      original_image_url: "https://via.placeholder.com/300x200?text=Waybill2",
      result_image_url: null,
      ocr_text: "另一个运单识别结果",
      ocr_confidence: 0.78,
      scan_time: "2015-10-03T15:00:00",
      status: "processing",
    },
  ],
  count: 2,
}

function WaybillsTable({ filters, refetchTrigger, onDataChange }: { 
  filters: any, 
  refetchTrigger: number,
  onDataChange: () => void
}) {
  const showToast = useCustomToast()
  
  // 使用内部状态管理分页，不更新URL
  const [currentPage, setCurrentPage] = useState(1)
  
  // 选中的记录状态
  const [selectedRecord, setSelectedRecord] = useState<ExtendedOCRRecord | null>(null)
  
  // 编辑模式状态
  const [isEditMode, setIsEditMode] = useState(false)
  const [editFormData, setEditFormData] = useState({
    waybill_number: '',
    carrier: '',
    shipping_date: '',
    recipient: '',
    delivery_date: ''
  })
  const [originalData, setOriginalData] = useState({
    waybill_number: '',
    carrier: '',
    shipping_date: '',
    recipient: '',
    delivery_date: ''
  })

  const {
    data: waybillsData,
    isLoading,
  } = useQuery({
    queryKey: ["waybills", { 
      page: currentPage, 
      ...filters,
      refetchTrigger
    }],
    queryFn: async () => {
      try {
        // 使用OcrService调用API
        const skip = (currentPage - 1) * PER_PAGE
        const limit = PER_PAGE
        
        // 注意：当前OcrService.getOcrResults只支持deviceSn, skip, limit参数
        // 其他筛选参数暂时通过设备序列号模拟或需要后端API更新
        const data = await OcrService.getOcrResults({
          skip,
          limit,
          deviceSn: filters.waybill_number || undefined, // 暂时用waybill_number作为deviceSn搜索
        })
        
        return data
        
      } catch (error) {
        console.error('查询运单数据失败:', error)
        // 如果API调用失败，暂时返回mock数据
        return mockWaybillData
      }
    },
    placeholderData: (prevData) => prevData,
  })

  const records = waybillsData?.data || mockWaybillData.data
  const count = waybillsData?.count || mockWaybillData.count

  // 当数据变化时，默认选中第一条记录
  useEffect(() => {
    if (records.length > 0) {
      // 始终选中第一条记录，无论之前是否有选中的记录
      const firstRecord = records[0] as ExtendedOCRRecord
      setSelectedRecord(firstRecord)
      // 初始化编辑表单数据
      initializeEditForm(firstRecord)
      // 退出编辑模式
      setIsEditMode(false)
    } else {
      setSelectedRecord(null)
      setIsEditMode(false)
    }
  }, [records]) // 只依赖records，不依赖selectedRecord

  // 当选中记录变化时，初始化编辑表单
  useEffect(() => {
    if (selectedRecord) {
      initializeEditForm(selectedRecord)
    }
  }, [selectedRecord])

  // 调试：监控 editFormData 变化
  useEffect(() => {
    console.log('editFormData changed:', editFormData)
  }, [editFormData])

  // 调试：监控 isEditMode 变化
  useEffect(() => {
    console.log('isEditMode changed:', isEditMode)
  }, [isEditMode])

  // 初始化编辑表单数据
  const initializeEditForm = (record: ExtendedOCRRecord) => {
    const formData = {
      waybill_number: record.waybill_number || record.device_sn || '',
      carrier: record.carrier || '',
      shipping_date: record.shipping_date ? 
        new Date(record.shipping_date).toISOString().split('T')[0] : '',
      recipient: record.recipient || '',
      delivery_date: record.delivery_date ? 
        new Date(record.delivery_date).toISOString().split('T')[0] : '',
      upload_date: record.upload_date ?
        new Date(record.upload_date).toISOString().split('T')[0] : ''
    }
    console.log('Initializing edit form with:', formData)
    console.log('Record data:', record)
    setEditFormData(formData)
    setOriginalData(formData)
  }

  // 进入编辑模式 - 使用更直接的方法
  const enterEditMode = () => {
    if (selectedRecord) {
      console.log('Entering edit mode for record:', selectedRecord)
      
      const formData = {
        waybill_number: selectedRecord.waybill_number || selectedRecord.device_sn || '',
        carrier: selectedRecord.carrier || '',
        shipping_date: selectedRecord.shipping_date ? 
          new Date(selectedRecord.shipping_date).toISOString().split('T')[0] : '',
        recipient: selectedRecord.recipient || '',
        delivery_date: selectedRecord.delivery_date ? 
          new Date(selectedRecord.delivery_date).toISOString().split('T')[0] : '',
        upload_date: selectedRecord.upload_date ?
          new Date(selectedRecord.upload_date).toISOString().split('T')[0] : ''
      }
      
      console.log('Setting form data:', formData)
      
      // 同时设置所有状态
      setEditFormData(formData)
      setOriginalData(formData)
      setIsEditMode(true)
      
      // 使用 setTimeout 确保状态更新后再检查
      setTimeout(() => {
        console.log('After state update - editFormData:', editFormData)
        console.log('After state update - isEditMode:', isEditMode)
      }, 100)
    }
  }

  // 保存修改
  const handleSave = async () => {
    if (!selectedRecord) return
    
    try {
      // 调用后端API保存数据
      const baseUrl = OpenAPI.BASE || 'http://localhost:8000'
      const response = await fetch(`${baseUrl}/api/v1/ocr/results/${selectedRecord.id}/waybill`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(editFormData),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '保存失败')
      }
      
      const updatedRecord = await response.json()
      
      showToast.showSuccessToast('数据保存成功')
      
      // 更新本地数据
      setSelectedRecord(updatedRecord as ExtendedOCRRecord)
      
      // 退出编辑模式
      setIsEditMode(false)
      
      // 触发数据重新获取以刷新列表
      onDataChange()
      
    } catch (error) {
      console.error('保存失败:', error)
      showToast.showErrorToast('保存失败: ' + (error instanceof Error ? error.message : '未知错误'))
    }
  }

  // 取消修改
  const handleCancel = () => {
    // 恢复原始数据
    setEditFormData(originalData)
    // 退出编辑模式
    setIsEditMode(false)
  }

  if (isLoading) {
    return (
      <Flex justify="center" align="center" h="400px">
        <Spinner size="xl" />
      </Flex>
    )
  }

  if (records.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Indicator>
            <FiSearch />
          </EmptyState.Indicator>
          <VStack textAlign="center">
            <EmptyState.Title>暂无运单记录</EmptyState.Title>
            <EmptyState.Description>
              上传运单图片进行识别后，结果将显示在这里
            </EmptyState.Description>
          </VStack>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <>
      <Text fontSize="lg" fontWeight="semibold" mb={4}>
        面单列表
      </Text>
      
      {/* 三栏布局 */}
      <Flex gap={4} align="start">
        {/* 第一栏：发货单号列表 */}
        <Box w="200px" flexShrink={0}>
          <Text fontSize="sm" fontWeight="semibold" mb={2} color="gray.600">
            发货单号
          </Text>
          <VStack gap={0} align="stretch" border="1px" borderColor="gray.200" borderRadius="md">
            {records.map((record: any, index: number) => (
              <Box
                key={record.id}
                p={3}
                bg={selectedRecord?.id === record.id ? "blue.50" : "white"}
                borderColor={selectedRecord?.id === record.id ? "blue.200" : "gray.200"}
                borderBottomWidth={index === records.length - 1 ? "0" : "1px"}
                cursor="pointer"
                _hover={{ bg: "gray.50" }}
                onClick={() => setSelectedRecord(record as ExtendedOCRRecord)}
              >
                <Text 
                  fontWeight={selectedRecord?.id === record.id ? "bold" : "medium"}
                  color={selectedRecord?.id === record.id ? "blue.600" : "gray.800"}
                  fontSize="sm"
                >
                  {record.waybill_number || record.device_sn}
                </Text>
              </Box>
            ))}
          </VStack>
        </Box>

        {/* 第二栏：货单信息 */}
        <Box w="300px" flexShrink={0}>
          <Text fontSize="sm" fontWeight="semibold" mb={2} color="gray.600">
            货单信息
          </Text>
          {selectedRecord && (
            <VStack align="start" gap={3} p={4} border="1px" borderColor="gray.200" borderRadius="md" bg="white">
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>发货单号</Text>
                {isEditMode ? (
                  <Input
                    size="sm"
                    value={editFormData.waybill_number || ''}
                    onChange={(e) => {
                      console.log('Waybill number changed:', e.target.value)
                      setEditFormData(prev => ({ ...prev, waybill_number: e.target.value }))
                    }}
                    placeholder="请输入发货单号"
                    onFocus={() => console.log('Waybill input focused, current value:', editFormData.waybill_number)}
                  />
                ) : (
                  <Text fontSize="sm" fontWeight="medium">{selectedRecord.waybill_number || selectedRecord.device_sn}</Text>
                )}
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>承运商</Text>
                {isEditMode ? (
                  <Input
                    size="sm"
                    value={editFormData.carrier || ''}
                    onChange={(e) => setEditFormData(prev => ({ ...prev, carrier: e.target.value }))}
                    placeholder="请输入承运商"
                  />
                ) : (
                  <Text fontSize="sm">{selectedRecord.carrier || "XXX物流"}</Text>
                )}
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>发货日期</Text>
                {isEditMode ? (
                  <Input
                    type="date"
                    size="sm"
                    value={editFormData.shipping_date ? editFormData.shipping_date.split('T')[0] : ''}
                    onChange={(e) => setEditFormData(prev => ({ ...prev, shipping_date: e.target.value }))}
                  />
                ) : (
                  <Text fontSize="sm">
                    {selectedRecord.shipping_date ? 
                      new Date(selectedRecord.shipping_date).toLocaleDateString("zh-CN") : 
                      "2015/10/02"
                    }
                  </Text>
                )}
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>签收人</Text>
                {isEditMode ? (
                  <Input
                    size="sm"
                    value={editFormData.recipient || ''}
                    onChange={(e) => setEditFormData(prev => ({ ...prev, recipient: e.target.value }))}
                    placeholder="请输入签收人"
                  />
                ) : (
                  <Text fontSize="sm">{selectedRecord.recipient || "li si"}</Text>
                )}
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>签收日期</Text>
                {isEditMode ? (
                  <Input
                    type="date"
                    size="sm"
                    value={editFormData.delivery_date ? editFormData.delivery_date.split('T')[0] : ''}
                    onChange={(e) => setEditFormData(prev => ({ ...prev, delivery_date: e.target.value }))}
                  />
                ) : (
                  <Text fontSize="sm">
                    {selectedRecord.delivery_date ? 
                      new Date(selectedRecord.delivery_date).toLocaleDateString("zh-CN") : 
                      "2015/10/10"
                    }
                  </Text>
                )}
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>上传日期</Text>
                <Text fontSize="sm">
                  {selectedRecord.upload_date ? 
                    new Date(selectedRecord.upload_date).toLocaleDateString("zh-CN") : 
                    new Date(selectedRecord.scan_time).toLocaleDateString("zh-CN")
                  }
                </Text>
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>上传人</Text>
                <Text fontSize="sm">{selectedRecord.uploader || "san zhang"}</Text>
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>审核状态</Text>
                <AuditStatusBadge status={selectedRecord.audit_status || "未审核"} />
              </Box>

              {/* 操作按钮 */}
              <HStack gap={2} mt={4} w="full">
                {isEditMode ? (
                  <>
                    <Button
                      size="sm"
                      colorScheme="green"
                      flex={1}
                      onClick={handleSave}
                    >
                      保存
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      flex={1}
                      onClick={handleCancel}
                    >
                      取消
                    </Button>
                  </>
                ) : (
                  <>
                    {/* 只有在未审核状态下才显示审核通过按钮、修改按钮和删除按钮 */}
                    {selectedRecord.audit_status !== "已审核" && (
                      <>
                        <Button
                          size="sm"
                          colorScheme="green"
                          flex={1}
                          onClick={() => handleApprove(String(selectedRecord.id))}
                        >
                          审核通过
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          flex={1}
                          onClick={() => handleEdit(String(selectedRecord.id))}
                        >
                          修改
                        </Button>
                        <Button
                          size="sm"
                          colorScheme="red"
                          variant="outline"
                          flex={1}
                          onClick={() => handleDelete(String(selectedRecord.id))}
                        >
                          删除
                        </Button>
                      </>
                    )}
                  </>
                )}
              </HStack>
            </VStack>
          )}
        </Box>

        {/* 第三栏：面单OCR结果图片 */}
        <Box flex={1}>
          <Text fontSize="sm" fontWeight="semibold" mb={2} color="gray.600">
            面单图片
          </Text>
          {selectedRecord ? (
            <ImageViewer 
              src={selectedRecord.result_image_url} 
              alt="面单图片" 
            />
          ) : (
            <Box
              w="100%"
              h="400px"
              bg="gray.100"
              _dark={{ bg: "gray.700" }}
              borderRadius="md"
              border="1px"
              borderColor="gray.200"
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Text fontSize="sm" color="gray.500">
                请选择发货单号查看图片
              </Text>
            </Box>
          )}
        </Box>
      </Flex>

      {/* 分页 */}
      <Flex justifyContent="space-between" alignItems="center" mt={6}>
        <Text fontSize="sm" color="gray.600">
          共 {count} 条记录，第 {currentPage} 页/共 {Math.ceil(count / PER_PAGE)} 页
        </Text>
        <HStack>
          <Button 
            size="sm" 
            disabled={currentPage === 1}
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
          >
            上一页
          </Button>
          <Text mx={4} fontSize="sm">
            第 {currentPage} 页
          </Text>
          <Button 
            size="sm" 
            disabled={currentPage >= Math.ceil(count / PER_PAGE)}
            onClick={() => setCurrentPage(prev => prev + 1)}
          >
            下一页
          </Button>
        </HStack>
      </Flex>
    </>
  )

  // 审核通过处理函数
  async function handleApprove(recordId: string) {
    console.log('Approve record:', recordId)
    
    // 校验面单内容是否完整
    if (!selectedRecord) return;
    
    // 检查必填字段是否都已填写
    const requiredFields = [
      { field: selectedRecord.waybill_number, name: '发货单号' },
      { field: selectedRecord.carrier, name: '承运商' },
      { field: selectedRecord.shipping_date, name: '发货日期' },
      { field: selectedRecord.recipient, name: '签收人' },
      { field: selectedRecord.delivery_date, name: '签收日期' }
    ];
    
    const missingFields = requiredFields.filter(item => !item.field);
    
    if (missingFields.length > 0) {
      // 使用自定义Toast显示错误，而不是alert
      showToast.showErrorToast("面单数据缺失，请人工补全");
      return;
    }
    
    try {
      // 调用后端API更新审核状态
      const baseUrl = OpenAPI.BASE || 'http://localhost:8000'
      const response = await fetch(`${baseUrl}/api/v1/ocr/results/${recordId}/audit`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ audit_status: "已审核" }),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '审核失败')
      }
      
      const updatedRecord = await response.json()
      
      // 更新本地数据
      setSelectedRecord(updatedRecord as ExtendedOCRRecord)
      
      // 显示成功消息（使用自定义Toast，不使用alert）
      showToast.showSuccessToast("审核已通过");
      
      // 触发数据重新获取以刷新列表
      onDataChange()
      
    } catch (error) {
      console.error('审核失败:', error)
      showToast.showErrorToast('审核失败: ' + (error instanceof Error ? error.message : '未知错误'))
    }
  }

  function handleEdit(recordId: string) {
    console.log('Edit record:', recordId)
    enterEditMode()
  }

  function handleDelete(recordId: string) {
    console.log('Delete record:', recordId)
    showToast.showSuccessToast("删除功能即将上线")
  }
}

function Waybills() {
  // 筛选条件状态 - 使用内部状态不更新URL，移除默认值
  const [filters, setFilters] = useState({
    upload_date_start: "",
    upload_date_end: "",
    shipping_date_start: "",
    shipping_date_end: "",
    delivery_date_start: "",
    delivery_date_end: "",
    waybill_number: "",
    carrier: "",
    recipient: "",
    audit_status: "全部",
  })

  // 获取WaybillsTable组件的引用以触发搜索
  const [shouldRefetch, setShouldRefetch] = useState(0)

  const handleSearch = () => {
    // 通过改变状态值来触发WaybillsTable重新获取数据
    setShouldRefetch(prev => prev + 1)
  }

  const handleReset = () => {
    const resetFilters = {
      upload_date_start: "",
      upload_date_end: "",
      shipping_date_start: "",
      shipping_date_end: "",
      delivery_date_start: "",
      delivery_date_end: "",
      waybill_number: "",
      carrier: "",
      recipient: "",
      audit_status: "全部",
    }
    setFilters(resetFilters)
    setShouldRefetch(prev => prev + 1)
  }

  const updateFilter = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  return (
    <Container maxW="full">
      {/* 筛选条件区域 - 三层结构布局 */}
      <Box mt={8} mb={6} p={4} borderRadius="lg">
        {/* 第一部分：标题 */}
        <Text fontSize="md" fontWeight="semibold" mb={4}>
          筛选条件
        </Text>
        
        {/* 第二部分：查询条件 */}
        <VStack gap={3} align="stretch" mb={4}>
          <HStack gap={4} wrap="wrap">
            {/* 上传日期 */}
            <HStack>
              <Text fontSize="sm" fontWeight="medium" minW="60px">上传日期</Text>
              <Input
                type="date"
                size="sm"
                w="140px"
                value={filters.upload_date_start}
                onChange={(e) => updateFilter('upload_date_start', e.target.value)}
              />
              <Text fontSize="sm">至</Text>
              <Input
                type="date"
                size="sm"
                w="140px"
                value={filters.upload_date_end}
                onChange={(e) => updateFilter('upload_date_end', e.target.value)}
              />
            </HStack>

            {/* 发货日期 */}
            <HStack>
              <Text fontSize="sm" fontWeight="medium" minW="60px">发货日期</Text>
              <Input
                type="date"
                size="sm"
                w="140px"
                value={filters.shipping_date_start}
                onChange={(e) => updateFilter('shipping_date_start', e.target.value)}
              />
              <Text fontSize="sm">至</Text>
              <Input
                type="date"
                size="sm"
                w="140px"
                value={filters.shipping_date_end}
                onChange={(e) => updateFilter('shipping_date_end', e.target.value)}
              />
            </HStack>

            {/* 签收日期 */}
            <HStack>
              <Text fontSize="sm" fontWeight="medium" minW="60px">签收日期</Text>
              <Input
                type="date"
                size="sm"
                w="140px"
                value={filters.delivery_date_start}
                onChange={(e) => updateFilter('delivery_date_start', e.target.value)}
              />
              <Text fontSize="sm">至</Text>
              <Input
                type="date"
                size="sm"
                w="140px"
                value={filters.delivery_date_end}
                onChange={(e) => updateFilter('delivery_date_end', e.target.value)}
              />
            </HStack>

            {/* 发货单号 */}
            <HStack>
              <Text fontSize="sm" fontWeight="medium" minW="60px">发货单号</Text>
              <Input
                placeholder="请输入发货单号"
                size="sm"
                w="150px"
                value={filters.waybill_number}
                onChange={(e) => updateFilter('waybill_number', e.target.value)}
              />
            </HStack>
          </HStack>

          <HStack gap={4} wrap="wrap">
            {/* 承运商 */}
            <HStack>
              <Text fontSize="sm" fontWeight="medium" minW="60px">承运商</Text>
              <Input
                placeholder="请输入承运商"
                size="sm"
                w="150px"
                value={filters.carrier}
                onChange={(e) => updateFilter('carrier', e.target.value)}
              />
            </HStack>

            {/* 签收人 */}
            <HStack>
              <Text fontSize="sm" fontWeight="medium" minW="60px">签收人</Text>
              <Input
                placeholder="请输入签收人"
                size="sm"
                w="150px"
                value={filters.recipient}
                onChange={(e) => updateFilter('recipient', e.target.value)}
              />
            </HStack>

            {/* 审核状态 */}
            <HStack>
              <Text fontSize="sm" fontWeight="medium" minW="60px">审核状态</Text>
              <select
                value={filters.audit_status}
                onChange={(e) => updateFilter('audit_status', e.target.value)}
                style={{
                  padding: '6px 8px',
                  borderRadius: '4px',
                  border: '1px solid #E2E8F0',
                  fontSize: '14px',
                  width: '120px',
                  height: '32px'
                }}
              >
                <option value="全部">全部</option>
                <option value="未审核">未审核</option>
                <option value="已审核">已审核</option>
                <option value="审核通过">审核通过</option>
                <option value="审核不通过">审核不通过</option>
              </select>
            </HStack>
          </HStack>
        </VStack>

        {/* 第三部分：操作按钮 */}
        <Flex justify="space-between" align="center">
          <HStack gap={2}>
            <Button
              onClick={handleSearch}
              colorScheme="blue"
              size="sm"
            >
              查询
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              size="sm"
            >
              重置
            </Button>
          </HStack>
          <UploadModal onUploadSuccess={() => setShouldRefetch(prev => prev + 1)} />
        </Flex>
      </Box>

      <WaybillsTable filters={filters} refetchTrigger={shouldRefetch} onDataChange={() => setShouldRefetch(prev => prev + 1)} />
    </Container>
  )
}

// 图片查看器组件
function ImageViewer({ src, alt }: { src?: string | null; alt: string }) {
  const [scale, setScale] = useState(1) // 缩放比例
  const [baseScale, setBaseScale] = useState(1) // 基准缩放比例（适应容器时的比例）
  const [position, setPosition] = useState({ x: 0, y: 0 }) // 图片位置
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  // 重置图片位置和缩放
  const resetImage = useCallback(() => {
    setScale(baseScale)
    setPosition({ x: 0, y: 0 })
  }, [baseScale])

  // 确保图片在容器内完整显示
  useEffect(() => {
    // 重置位置
    setPosition({ x: 0, y: 0 });
  }, [src]);

  // 图片加载完成后调整缩放
  const handleImageLoad = useCallback(() => {
    if (imageRef.current && containerRef.current) {
      const img = imageRef.current;
      const container = containerRef.current;
      
      // 获取图片的原始尺寸
      const imgWidth = img.naturalWidth;
      const imgHeight = img.naturalHeight;
      
      // 获取容器尺寸
      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;
      
      // 计算适合容器的缩放比例
      const scaleX = containerWidth / imgWidth;
      const scaleY = containerHeight / imgHeight;
      
      // 使用较小的缩放比例，确保图片完全显示在容器内
      const fitScale = Math.min(scaleX, scaleY);
      
      // 设置基准缩放比例
      setBaseScale(fitScale);
      // 应用基准缩放
      setScale(fitScale);
    }
  }, []);

  // 滚轮缩放
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    // 减小缩放步长，使缩放更平滑
    const delta = e.deltaY > 0 ? -0.05 : 0.05
    setScale(prevScale => {
      // 计算相对于基准缩放的新缩放值
      const relativeScale = prevScale / baseScale
      const newRelativeScale = Math.max(0.1, Math.min(3, relativeScale + delta)) // 限制在基准的0.1-3倍之间
      return newRelativeScale * baseScale
    })
  }, [baseScale])

  // 鼠标按下开始拖拽
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) { // 左键
      setIsDragging(true)
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      })
    }
  }, [position])

  // 鼠标移动拖拽
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      })
    }
  }, [isDragging, dragStart])

  // 鼠标抬起结束拖拽
  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  // 双击重置
  const handleDoubleClick = useCallback(() => {
    resetImage()
  }, [resetImage])

  // 组件卸载时清理事件
  useEffect(() => {
    const handleGlobalMouseUp = () => setIsDragging(false)
    document.addEventListener('mouseup', handleGlobalMouseUp)
    return () => document.removeEventListener('mouseup', handleGlobalMouseUp)
  }, [])

  if (!src) {
    return (
      <Box
        w="100%"
        h="400px"
        bg="gray.100"
        _dark={{ bg: "gray.700" }}
        borderRadius="md"
        border="1px"
        borderColor="gray.200"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <Text fontSize="sm" color="gray.500">
          无图片
        </Text>
      </Box>
    )
  }

  return (
    <VStack spacing={2} align="stretch">
      <Box
        ref={containerRef}
        w="100%"
        h="400px"
        bg="gray.50"
        borderRadius="md"
        border="1px"
        borderColor="gray.200"
        overflow="hidden"
        position="relative"
        cursor={isDragging ? 'grabbing' : 'grab'}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onDoubleClick={handleDoubleClick}
        userSelect="none"
      >
        <Image
          ref={imageRef}
          src={src}
          alt={alt}
          position="absolute"
          top="50%"
          left="50%"
          transform={`translate(calc(-50% + ${position.x}px), calc(-50% + ${position.y}px)) scale(${scale})`}
          transformOrigin="center"
          maxW="none"
          maxH="none"
          pointerEvents="none"
          transition={isDragging ? 'none' : 'transform 0.1s ease-out'}
          onLoad={handleImageLoad}
        />
        
        {/* 缩放指示器和重置按钮 */}
        <Flex
          position="absolute"
          top={2}
          right={2}
          alignItems="center"
          gap={2}
        >
          <Text
            bg="blackAlpha.700"
            color="white"
            px={2}
            py={1}
            borderRadius="md"
            fontSize="xs"
          >
            缩放: {Math.round((scale / baseScale) * 100)}%
          </Text>
          <Button
            size="xs"
            colorScheme="blue"
            onClick={resetImage}
          >
            重置
          </Button>
        </Flex>
      </Box>
      
      {/* 操作提示 */}
      <Text
        fontSize="xs"
        color="gray.500"
        textAlign="center"
        mt={1}
      >
        滚轮缩放 · 拖拽查看 · 双击重置
      </Text>
    </VStack>
  )
}

// 审核状态徽章组件
function AuditStatusBadge({ status }: { status: string }) {
  const getStatusProps = (status: string) => {
    switch (status) {
      case "审核通过":
        return { color: "green.600", label: "审核通过" }
      case "审核不通过":
        return { color: "red.600", label: "审核不通过" }
      case "已审核":
        return { color: "green.600", label: "已审核" }
      case "未审核":
        return { color: "red.600", label: "未审核" }
      default:
        return { color: "gray.600", label: status }
    }
  }

  const { color, label } = getStatusProps(status)

  return <Text fontSize="sm" color={color} fontWeight="medium">{label}</Text>
}

// 文件上传模态框组件
function UploadModal({ onUploadSuccess }: { onUploadSuccess: () => void }) {
  const [isOpen, setIsOpen] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [uploadFiles, setUploadFiles] = useState<File[]>([])
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadedCount, setUploadedCount] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const showToast = useCustomToast()
  const queryClient = useQueryClient()

  // 支持的文件格式
  const ACCEPTED_FILE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/webp', 'application/pdf']
  const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

  // 面单上传处理mutation
  const waybillUploadMutation = useMutation({
    mutationFn: async (file: File) => {
      // 创建FormData对象
      const formData = new FormData()
      formData.append('image_file', file)
      // 不提供device_sn，让后端自动生成
      
      // 直接调用后端API，使用正确的基础URL
      const baseUrl = OpenAPI.BASE || 'http://localhost:8000'
      const response = await fetch(`${baseUrl}/api/v1/ocr/upload-waybill`, {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '上传失败')
      }
      
      return await response.json()
    },
    onSuccess: () => {
      showToast.showSuccessToast('面单上传并识别成功！')
      setUploadFiles([])
      setIsOpen(false)
      onUploadSuccess()
      queryClient.invalidateQueries({ queryKey: ["waybills"] })
    },
    onError: (error: Error) => {
      console.error('面单上传失败:', error)
      showToast.showErrorToast('面单上传失败: ' + (error.message || '未知错误'))
    },
    onSettled: () => {
      setIsUploading(false)
      setUploadProgress(0)
    }
  })

  // 验证文件格式和大小
  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_FILE_TYPES.includes(file.type)) {
      return '不支持的文件格式。仅支持 JPG、JPEG、PNG、BMP、WEBP、PDF 格式'
    }
    if (file.size > MAX_FILE_SIZE) {
      return '文件大小超过限制。最大支持 10MB'
    }
    return null
  }

  // 处理文件选择
  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return

    const validFiles: File[] = []
    let hasError = false

    // 检查所有文件
    Array.from(files).forEach(file => {
      const error = validateFile(file)
      if (error) {
        showToast.showErrorToast(`文件 ${file.name}: ${error}`)
        hasError = true
      } else {
        validFiles.push(file)
      }
    })

    if (!hasError && validFiles.length > 0) {
      setUploadFiles(prev => [...prev, ...validFiles])
    }
  }

  // 处理拖拽事件
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files)
    }
  }, [])

  // 上传文件
  const handleUpload = async () => {
    if (uploadFiles.length === 0) return
    
    setIsUploading(true)
    setUploadProgress(0)
    setUploadedCount(0)
    
    try {
      // 处理所有文件
      for (let i = 0; i < uploadFiles.length; i++) {
        const file = uploadFiles[i]
        try {
          await waybillUploadMutation.mutateAsync(file)
          setUploadedCount(prev => prev + 1)
          setUploadProgress(((i + 1) / uploadFiles.length) * 100)
        } catch (error) {
          showToast.showErrorToast(`文件 ${file.name} 上传失败`)
        }
      }
      
      // 全部完成后
      setUploadProgress(100)
      showToast.showSuccessToast('文件上传完成')
      onUploadSuccess()
      handleClose()
    } catch (error) {
      setUploadProgress(0)
      showToast.showErrorToast('上传过程中发生错误')
    }
  }

  // 重置状态
  // 重置状态
  const handleClose = () => {
    setIsOpen(false)
    setUploadFiles([])
    setUploadProgress(0)
    setUploadedCount(0)
    setIsUploading(false)
    setDragActive(false)
  }

  return (
    <DialogRoot
      size={{ base: "sm", md: "lg" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => {
        if (!open) handleClose()
        else setIsOpen(true)
      }}
    >
      <DialogTrigger asChild>
        <Button
          colorScheme="green"
          size="sm"
        >
          <FiUpload />
          新增
        </Button>
      </DialogTrigger>
      
      <DialogContent>
        <DialogHeader>
          <DialogTitle>上传运单文件</DialogTitle>
        </DialogHeader>
        
        <DialogBody>
          <VStack gap={4} align="stretch">
            {/* <Text fontSize="sm" color="gray.600">
              支持格式：JPG、JPEG、PNG、BMP、WEBP、PDF，最大 10MB
            </Text> */}
            
            {/* 文件上传区域 */}
            <Box
              border="2px dashed"
              borderColor={dragActive ? "blue.400" : "gray.300"}
              borderRadius="lg"
              p={8}
              textAlign="center"
              bg={dragActive ? "blue.50" : "gray.50"}
              _hover={{ bg: "gray.100", borderColor: "gray.400" }}
              cursor="pointer"
              transition="all 0.2s"
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Input
                ref={fileInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.bmp,.webp,.pdf"
                multiple
                onChange={(e) => handleFileSelect(e.target.files)}
                display="none"
              />
              
              {uploadFiles.length > 0 ? (
                <VStack gap={3} w="full">
                  <FiFile size={48} color="green" />
                  <Text fontWeight="medium" color="green.600">
                    已选择 {uploadFiles.length} 个文件
                  </Text>
                  <VStack gap={2} w="full" maxH="200px" overflowY="auto">
                    {uploadFiles.map((file, index) => (
                      <Flex
                        key={index}
                        justify="space-between"
                        align="center"
                        w="full"
                        p={2}
                        bg="gray.50"
                        borderRadius="md"
                        border="1px"
                        borderColor="gray.200"
                      >
                        <VStack align="start" gap={0} flex={1}>
                          <Text fontSize="sm" fontWeight="medium" truncate>
                            {file.name}
                          </Text>
                          <Text fontSize="xs" color="gray.500">
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </Text>
                        </VStack>
                        <Button
                          size="xs"
                          variant="ghost"
                          colorScheme="red"
                          onClick={(e) => {
                            e.stopPropagation()
                            setUploadFiles(prev => prev.filter((_, i) => i !== index))
                          }}
                        >
                          <FiX />
                        </Button>
                      </Flex>
                    ))}
                  </VStack>
                  <Text fontSize="xs" color="gray.500" textAlign="center">
                    单个文件或多个文件都可以自动识别
                  </Text>
                </VStack>
              ) : (
                <VStack gap={3}>
                  <Box color={dragActive ? "blue.500" : "gray.400"}>
                    <FiUpload size={48} />
                  </Box>
                  <VStack gap={1}>
                    <Text fontWeight="medium" color={dragActive ? "blue.600" : "gray.700"}>
                      {dragActive ? "释放文件到此处上传" : "点击或拖拽文件到这里上传"}
                    </Text>
                    <Text fontSize="sm" color="blue.500" fontWeight="medium">
                      支持格式：jpg、jpeg、png、bmp、webp、pdf
                    </Text>
                    <Text fontSize="sm" color="gray.500">
                      单个文件或多个文件都可以自动识别
                    </Text>
                    <Text fontSize="sm" color="gray.500">
                      点击确定，提交文件上传
                    </Text>
                  </VStack>
                  <Button
                    colorScheme="blue"
                    size="md"
                    onClick={(e) => {
                      e.stopPropagation()
                      fileInputRef.current?.click()
                    }}
                  >
                    选择文件
                  </Button>
                </VStack>
              )}
            </Box>
            
            {/* 上传进度 */}
            {isUploading && (
              <VStack gap={2}>
                <Box w="100%" bg="gray.200" borderRadius="md" h="2">
                  <Box 
                    bg="blue.500" 
                    h="100%" 
                    borderRadius="md"
                    width={`${uploadProgress}%`}
                    transition="width 0.3s ease"
                  />
                </Box>
                <Text fontSize="sm" color="gray.600">
                  上传中，请勿关闭页面（{uploadedCount}/{uploadFiles.length}）
                </Text>
              </VStack>
            )}
          </VStack>
        </DialogBody>
        
        <DialogFooter gap={2}>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isUploading}
          >
            取消
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleUpload}
            disabled={uploadFiles.length === 0 || isUploading}
            loading={isUploading}
          >
            {isUploading ? "处理中..." : "确定"}
          </Button>
        </DialogFooter>
        
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}