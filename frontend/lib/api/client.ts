import axios, { AxiosError } from "axios";
import { publicEnv } from "@/lib/env";

export type ApiError = {
  status?: number;
  message: string;
  details?: unknown;
};

export const apiClient = axios.create({
  baseURL: publicEnv.NEXT_PUBLIC_API_BASE_PATH,
  headers: {
    "X-Requested-With": "XMLHttpRequest"
  },
  withCredentials: false
});

apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError) => {
    const status = error.response?.status;
    const responseData = error.response?.data as { detail?: unknown; message?: string } | undefined;
    const message =
      typeof responseData?.detail === "string"
        ? responseData.detail
        : typeof responseData?.message === "string"
          ? responseData.message
          : error.message || "Request failed";

    return Promise.reject<ApiError>({
      status,
      message,
      details: responseData?.detail ?? responseData ?? undefined
    });
  }
);

