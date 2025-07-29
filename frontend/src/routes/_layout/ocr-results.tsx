import {
  Badge,
  Box,
  Container,
  Flex,
  Heading,
  HStack,
  Image,
  Input,
  Table,
  VStack,
  Button,
  Spinner,
  Text,
  IconButton,
  EmptyState,
} from "@chakra-ui/react"
import { InputGroup } from "@/components/ui/input-group"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { FiEye, FiDownload, FiTrash2, FiSearch, FiX } from "react-icons/fi"
import { z } from "zod"
import { useState, useEffect } from "react"

import { type ApiError, OcrService, type OCRRecordPublic } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import {
  DialogRoot,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogCloseTrigger,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "@/components/ui/pagination.tsx"

const ocrResultsSearchSchema = z.object({
  page: z.number().catch(1),
  device_sn: z.string().optional(),
})

export const Route = createFileRoute("/_layout/ocr-results")({
  component: OCRResults,
  validateSearch: ocrResultsSearchSchema,
})

const PER_PAGE = 10

// Mock data for development
const mockOCRData = {
  data: [
    {
      id: "1",
      device_sn: "DEV001",
      original_image_url: "https://via.placeholder.com/300x200?text=Original",
      result_image_url: "https://via.placeholder.com/300x200?text=Result",
      ocr_text: "这是一个示例OCR识别文本",
      ocr_confidence: 0.95,
      scan_time: new Date().toISOString(),
      status: "success",
    },
    {
      id: "2", 
      device_sn: "DEV002",
      original_image_url: "https://via.placeholder.com/300x200?text=Original2",
      result_image_url: null,
      ocr_text: "另一个识别结果",
      ocr_confidence: 0.78,
      scan_time: new Date().toISOString(),
      status: "processing",
    },
  ],
  count: 2,
}

function OCRResultsTable() {
  const navigate = useNavigate({ from: Route.fullPath })
  const queryClient = useQueryClient()
  const showToast = useCustomToast()
  const { page, device_sn } = Route.useSearch()

  const setPage = (page: number) =>
    navigate({
      search: (prev: { [key: string]: string }) => ({ ...prev, page }),
    })

  const setDeviceSn = (deviceSn: string) =>
    navigate({
      search: (prev: { [key: string]: string }) => ({ 
        ...prev, 
        device_sn: deviceSn || undefined,
        page: 1 
      }),
    })

  // TODO: Replace with actual API call when OCRService is available
  const {
    data: ocrResultsData,
    isLoading,
    isPlaceholderData,
  } = useQuery({
    queryKey: ["ocr-results", { page, device_sn }],
    queryFn: () =>
      OcrService.getOcrResults({
        skip: (page - 1) * PER_PAGE,
        limit: PER_PAGE,
        deviceSn: device_sn,
      }),
    placeholderData: (prevData) => prevData,
  })

  const records = ocrResultsData?.data || []
  const count = ocrResultsData?.count || 0

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
            <EmptyState.Title>暂无OCR记录</EmptyState.Title>
            <EmptyState.Description>
              上传图片进行OCR识别后，结果将显示在这里
            </EmptyState.Description>
          </VStack>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <>
      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader w="sm">设备SN</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">原图预览</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">结果图预览</Table.ColumnHeader>
            <Table.ColumnHeader w="lg">识别文本</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">置信度</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">扫描时间</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">状态</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">操作</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {records.map((record: OCRRecordPublic) => (
            <Table.Row key={record.id} opacity={isPlaceholderData ? 0.5 : 1}>
              <Table.Cell truncate maxW="sm" fontWeight="medium">
                {record.device_sn}
              </Table.Cell>
              <Table.Cell>
                <ImagePreview src={record.original_image_url} alt="原图" />
              </Table.Cell>
              <Table.Cell>
                <ImagePreview src={record.result_image_url} alt="结果图" />
              </Table.Cell>
              <Table.Cell 
                color={!record.ocr_text ? "gray" : "inherit"}
                truncate 
                maxW="30%"
              >
                {record.ocr_text || "N/A"}
              </Table.Cell>
              <Table.Cell>
                {record.ocr_confidence ? (
                  <Badge
                    colorScheme={
                      record.ocr_confidence > 0.8
                        ? "green"
                        : record.ocr_confidence > 0.6
                        ? "yellow"
                        : "red"
                    }
                  >
                    {(record.ocr_confidence * 100).toFixed(1)}%
                  </Badge>
                ) : (
                  "N/A"
                )}
              </Table.Cell>
              <Table.Cell truncate maxW="sm">
                {record.scan_time ? new Date(record.scan_time).toLocaleString("zh-CN") : "N/A"}
              </Table.Cell>
              <Table.Cell>
                <StatusBadge status={record.status || "unknown"} />
              </Table.Cell>
              <Table.Cell>
                <HStack gap={1}>
                  <IconButton
                    aria-label="查看详情"
                    size="sm"
                    variant="ghost"
                    title="查看详情"
                    onClick={() => showToast.showSuccessToast("详情页面即将上线")}
                  >
                    <FiEye />
                  </IconButton>
                  <IconButton
                    aria-label="下载结果"
                    size="sm"
                    variant="ghost"
                    title="下载结果"
                    onClick={() => handleDownload(String(record.id))}
                  >
                    <FiDownload />
                  </IconButton>
                  <IconButton
                    aria-label="删除记录"
                    size="sm"
                    variant="ghost"
                    colorPalette="red"
                    title="删除记录"
                    onClick={() => handleDelete(String(record.id))}
                  >
                    <FiTrash2 />
                  </IconButton>
                </HStack>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
      <Flex justifyContent="flex-end" mt={4}>
        <PaginationRoot
          count={count}
          pageSize={PER_PAGE}
          onPageChange={({ page }) => setPage(page)}
        >
          <Flex>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </Flex>
        </PaginationRoot>
      </Flex>
    </>
  )

  function handleDownload(recordId: string) {
    // TODO: 实现下载功能
    showToast.showSuccessToast("下载功能即将上线")
  }

  function handleDelete(recordId: string) {
    // TODO: 实现删除功能
    showToast.showSuccessToast("删除功能即将上线")
  }
}

function OCRResults() {
  const { device_sn } = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const [inputValue, setInputValue] = useState(device_sn || "")

  // 同步URL参数变化到本地state
  useEffect(() => {
    setInputValue(device_sn || "")
  }, [device_sn])

  const handleSearch = () => {
    navigate({
      search: (prev: { [key: string]: string }) => ({ 
        ...prev, 
        device_sn: inputValue || undefined,
        page: 1 
      }),
    })
  }

  const handleClear = () => {
    setInputValue("")
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <Container maxW="full">
      <Heading size="lg" pt={12}>
        OCR结果管理
      </Heading>

      {/* 美化的筛选区域 - SN输入框和标签在同一行 */}
      <Box mt={8} mb={6}>
        <HStack gap={4} align="center">
          <Text fontSize="sm" fontWeight="medium" color="gray.700" _dark={{ color: "gray.300" }} minW="fit-content">
            设备序列号
          </Text>
          <InputGroup
            flex="1"
            maxW="300px"
            endElement={
              inputValue ? (
                <IconButton
                  aria-label="清除输入"
                  size="xs"
                  variant="ghost"
                  onClick={handleClear}
                >
                  <FiX />
                </IconButton>
              ) : null
            }
          >
            <Input
              placeholder="输入设备SN筛选"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              size="md"
              borderRadius="md"
              borderColor="gray.200"
              _dark={{ borderColor: "gray.600" }}
              _focus={{
                borderColor: "blue.500",
                boxShadow: "0 0 0 1px #3182ce",
              }}
              _hover={{
                borderColor: "gray.300",
                _dark: { borderColor: "gray.500" }
              }}
            />
          </InputGroup>
          <Button
            onClick={handleSearch}
            colorScheme="blue"
            size="md"
          >
            <FiSearch />
            查询
          </Button>
        </HStack>
      </Box>

      <OCRResultsTable />
    </Container>
  )
}

// 图片预览组件
function ImagePreview({ src, alt }: { src?: string | null; alt: string }) {
  const [isOpen, setIsOpen] = useState(false)

  if (!src) {
    return (
      <Box
        w="50px"
        h="50px"
        bg="gray.100"
        _dark={{ bg: "gray.700" }}
        borderRadius="md"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <Text fontSize="xs" color="gray.500">
          无图片
        </Text>
      </Box>
    )
  }

  return (
    <DialogRoot open={isOpen} onOpenChange={(e) => setIsOpen(e.open)}>
      <DialogTrigger asChild>
        <Image
          src={src}
          alt={alt}
          w="50px"
          h="50px"
          objectFit="cover"
          borderRadius="md"
          cursor="pointer"
          _hover={{ opacity: 0.8 }}
        />
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{alt}</DialogTitle>
          <DialogCloseTrigger />
        </DialogHeader>
        <DialogBody pb={6}>
          <Image src={src} alt={alt} w="100%" borderRadius="md" />
        </DialogBody>
      </DialogContent>
    </DialogRoot>
  )
}

// 状态徽章组件
function StatusBadge({ status }: { status: string }) {
  const getStatusProps = (status: string) => {
    switch (status) {
      case "success":
        return { colorScheme: "green", label: "已完成" }
      case "failed":
        return { colorScheme: "red", label: "失败" }
      case "processing":
        return { colorScheme: "blue", label: "处理中" }
      default:
        return { colorScheme: "gray", label: status }
    }
  }

  const { colorScheme, label } = getStatusProps(status)

  return <Badge colorScheme={colorScheme}>{label}</Badge>
} 