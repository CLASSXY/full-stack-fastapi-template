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
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { FiSearch } from "react-icons/fi"
import { useState, useEffect, useRef, useCallback } from "react"

// Import API client
import { OcrService, type OCRRecordPublic } from "../../client"


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
    alert(message)
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

function WaybillsTable({ filters, refetchTrigger }: { filters: any, refetchTrigger: number }) {
  const showToast = useCustomToast()
  
  // 使用内部状态管理分页，不更新URL
  const [currentPage, setCurrentPage] = useState(1)
  
  // 选中的记录状态
  const [selectedRecord, setSelectedRecord] = useState<ExtendedOCRRecord | null>(null)

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
      setSelectedRecord(records[0] as ExtendedOCRRecord)
    } else {
      setSelectedRecord(null)
    }
  }, [records]) // 只依赖records，不依赖selectedRecord

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
                <Text fontSize="sm" fontWeight="medium">{selectedRecord.waybill_number || selectedRecord.device_sn}</Text>
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>承运商</Text>
                <Text fontSize="sm">{selectedRecord.carrier || "XXX物流"}</Text>
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>发货日期</Text>
                <Text fontSize="sm">
                  {selectedRecord.shipping_date ? 
                    new Date(selectedRecord.shipping_date).toLocaleDateString("zh-CN") : 
                    "2015/10/02"
                  }
                </Text>
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>签收人</Text>
                <Text fontSize="sm">{selectedRecord.recipient || "li si"}</Text>
              </Box>
              
              <Box w="full">
                <Text fontSize="xs" fontWeight="medium" color="gray.500" mb={1}>签收日期</Text>
                <Text fontSize="sm">
                  {selectedRecord.delivery_date ? 
                    new Date(selectedRecord.delivery_date).toLocaleDateString("zh-CN") : 
                    "2015/10/10"
                  }
                </Text>
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

  function handleApprove(recordId: string) {
    console.log('Approve record:', recordId)
    showToast.showSuccessToast("审核通过功能即将上线")
  }

  function handleEdit(recordId: string) {
    console.log('Edit record:', recordId)
    showToast.showSuccessToast("修改功能即将上线")
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
      <Heading size="lg" pt={12}>
        面单列表
      </Heading>

      {/* 筛选条件区域 - 紧凑横向布局 */}
      <Box mt={8} mb={6} p={4} bg="gray.50" _dark={{ bg: "gray.800" }} borderRadius="lg">
        <Text fontSize="md" fontWeight="semibold" mb={3}>
          筛选条件
        </Text>
        
        {/* 第一行：日期筛选 */}
        <VStack gap={3} align="stretch">
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

          {/* 第二行：其他筛选 */}
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

            {/* 操作按钮 */}
            <HStack gap={2} ml={4}>
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
              <Button
                colorScheme="green"
                size="sm"
                onClick={() => {/* TODO: 实现新增功能 */}}
              >
                新增
              </Button>
            </HStack>
          </HStack>
        </VStack>
      </Box>

      <WaybillsTable filters={filters} refetchTrigger={shouldRefetch} />
    </Container>
  )
}

// 图片查看器组件
function ImageViewer({ src, alt }: { src?: string | null; alt: string }) {
  const [scale, setScale] = useState(1) // 缩放比例
  const [position, setPosition] = useState({ x: 0, y: 0 }) // 图片位置
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  // 滚轮缩放
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    setScale(prevScale => {
      const newScale = Math.max(0.1, Math.min(3, prevScale + delta)) // 限制在0.1-3倍之间
      return newScale
    })
  }, [])

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
    setScale(1)
    setPosition({ x: 0, y: 0 })
  }, [])

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
      />
      
      {/* 缩放指示器 */}
      <Box
        position="absolute"
        bottom={2}
        right={2}
        bg="blackAlpha.700"
        color="white"
        px={2}
        py={1}
        borderRadius="md"
        fontSize="xs"
      >
        {Math.round(scale * 100)}%
      </Box>
    </Box>
  )
}

// 审核状态徽章组件
function AuditStatusBadge({ status }: { status: string }) {
  const getStatusProps = (status: string) => {
    switch (status) {
      case "审核通过":
        return { colorScheme: "green", label: "审核通过" }
      case "审核不通过":
        return { colorScheme: "red", label: "审核不通过" }
      case "已审核":
        return { colorScheme: "blue", label: "已审核" }
      case "未审核":
        return { colorScheme: "gray", label: "未审核" }
      default:
        return { colorScheme: "gray", label: status }
    }
  }

  const { colorScheme, label } = getStatusProps(status)

  return <Badge colorScheme={colorScheme}>{label}</Badge>
}